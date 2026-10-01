import "server-only";

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { cache } from "react";

import { DEFAULT_MOCK_DATA_DIR } from "@/lib/constants";
import {
  buildRecordTimeline,
  type TimelineItem,
} from "@/lib/nursingRecordTimeline";
import type {
  DailyManifest,
  PatientDailyFile,
  PatientStatus,
} from "@/types/dailyPackage";
import type { Sex } from "@/types/ward";

// 前端唯一直接讀檔的例外（見 ADR 0010）：只讀 mock_data/，之後改為後端 API
const PACKAGE_DIR_PATTERN = /^\d{8}$/;
const PACKAGE_FILE_PATTERN = /^[^/\\]+\.json$/;
const PATIENT_FILE_BLOCKS = [
  "daily_physical_assessments",
  "nursing_progress_notes",
  "transfers",
  "consultations",
  "medication_orders",
  "vital_signs",
  "lab_results",
] as const;

/** 護理紀錄頁左側的病患清單項目。 */
export type MockPatientSummary = {
  patientId: string;
  bedCode: string;
  sex: Sex;
  ageYears: number;
  diagnosis: string;
  status: PatientStatus;
  /** 第一個與最後一個有資料的業務日期（YYYY-MM-DD） */
  firstDate: string;
  lastDate: string;
};

export type NursingRecordsLoadResult =
  | {
      ok: true;
      wardName: string;
      patients: MockPatientSummary[];
      /** 查無指定病患時為 `undefined` */
      patient: MockPatientSummary | undefined;
      items: TimelineItem[];
    }
  | { ok: false; message: string };

type PackageEntry = { dir: string; manifest: DailyManifest };

type PatientSpan = {
  firstDate: string;
  lastDate: string;
  lastDir: string;
  lastFile: string;
};

/** 可直接顯示的繁中錯誤；訊息不含病患代碼。 */
class MockDataError extends Error {}

function getMockDataDir(): string {
  const dir = process.env.MOCK_DATA_DIR ?? DEFAULT_MOCK_DATA_DIR;
  return path.resolve(process.cwd(), dir);
}

/** 檔名只接受 manifest 與日期資料夾的固定格式，解析後仍須在假資料目錄內。 */
function resolvePackagePath(dir: string, fileName: string): string {
  if (!PACKAGE_DIR_PATTERN.test(dir) || !PACKAGE_FILE_PATTERN.test(fileName)) {
    throw new MockDataError(`資料包 ${dir} 含有格式不符的檔名`);
  }
  const root = getMockDataDir();
  const filePath = path.resolve(root, dir, fileName);
  if (!filePath.startsWith(`${root}${path.sep}`)) {
    throw new MockDataError(`資料包 ${dir} 含有格式不符的檔名`);
  }
  return filePath;
}

async function readJson(filePath: string): Promise<unknown> {
  return JSON.parse(await readFile(filePath, "utf-8"));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// 只檢查骨架；欄位細節以 docs/hospital-data-spec/*.schema.json 為準
function isManifest(value: unknown): value is DailyManifest {
  return (
    isRecord(value) &&
    typeof value.business_date === "string" &&
    Array.isArray(value.patients) &&
    value.patients.every(isRecord)
  );
}

function isPatientDailyFile(value: unknown): value is PatientDailyFile {
  return (
    isRecord(value) &&
    typeof value.schema_version === "string" &&
    isRecord(value.patient) &&
    PATIENT_FILE_BLOCKS.every((block) => Array.isArray(value[block]))
  );
}

async function readPackageManifest(dir: string): Promise<PackageEntry> {
  const manifest = await readJson(resolvePackagePath(dir, "manifest.json"));
  if (!isManifest(manifest)) {
    throw new MockDataError(`資料包 ${dir} 的 manifest.json 格式不符`);
  }
  return { dir, manifest };
}

async function readPatientFile(
  dir: string,
  fileName: string,
): Promise<PatientDailyFile> {
  const file = await readJson(resolvePackagePath(dir, fileName));
  if (!isPatientDailyFile(file)) {
    throw new MockDataError(`資料包 ${dir} 有病患檔案格式不符`);
  }
  return file;
}

/** 依日期由舊到新列出所有資料包（含各自的 manifest）。 */
const listPackages = cache(async (): Promise<PackageEntry[]> => {
  const entries = await readdir(getMockDataDir(), { withFileTypes: true });
  const dirs = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => PACKAGE_DIR_PATTERN.test(name))
    .sort();
  return Promise.all(dirs.map(readPackageManifest));
});

function collectPatientSpans(
  packages: readonly PackageEntry[],
): Map<string, PatientSpan> {
  const spans = new Map<string, PatientSpan>();
  for (const { dir, manifest } of packages) {
    for (const { patient_id, file } of manifest.patients) {
      spans.set(patient_id, {
        firstDate: spans.get(patient_id)?.firstDate ?? manifest.business_date,
        lastDate: manifest.business_date,
        lastDir: dir,
        lastFile: file,
      });
    }
  }
  return spans;
}

/** 病患基本資料取自最後一天的檔案（狀態為最新）。 */
async function toPatientSummary(span: PatientSpan) {
  const { patient } = await readPatientFile(span.lastDir, span.lastFile);
  return {
    patientId: patient.patient_id,
    bedCode: patient.bed_code,
    sex: patient.sex,
    ageYears: patient.age_years,
    diagnosis: patient.admission_diagnosis,
    status: patient.status,
    firstDate: span.firstDate,
    lastDate: span.lastDate,
  } satisfies MockPatientSummary;
}

/** 依第一次出現的日期排序的病患清單。 */
async function listMockPatients(
  packages: readonly PackageEntry[],
): Promise<MockPatientSummary[]> {
  const spans = [...collectPatientSpans(packages).values()];
  return Promise.all(spans.map(toPatientSummary));
}

/** 該病患每天的檔案，依日期由舊到新。 */
async function readPatientDailyFiles(
  packages: readonly PackageEntry[],
  patientId: string,
): Promise<PatientDailyFile[]> {
  const refs = packages.flatMap(({ dir, manifest }) =>
    manifest.patients
      .filter((patient) => patient.patient_id === patientId)
      .map((patient) => ({ dir, file: patient.file })),
  );
  return Promise.all(refs.map(({ dir, file }) => readPatientFile(dir, file)));
}

function hasErrorCode(error: unknown, code: string): boolean {
  return error instanceof Error && "code" in error && error.code === code;
}

function toLoadErrorMessage(error: unknown): string {
  if (error instanceof MockDataError) {
    return error.message;
  }
  if (hasErrorCode(error, "ENOENT")) {
    return "找不到假資料目錄或檔案，請確認 MOCK_DATA_DIR 設定（預設為專案根目錄的 mock_data/）";
  }
  if (error instanceof SyntaxError) {
    return "假資料 JSON 無法解析，請確認檔案內容";
  }
  return "讀取假資料時發生未預期的錯誤";
}

/**
 * 讀取護理紀錄頁所需的資料：病患清單，以及所選病患的紀錄時間軸。
 * 沒有指定病患時顯示第一位；讀檔失敗時回傳可顯示的訊息，不讓頁面整個失敗。
 */
export async function loadNursingRecords(
  requestedPatientId: string | undefined,
): Promise<NursingRecordsLoadResult> {
  try {
    const packages = await listPackages();
    const patients = await listMockPatients(packages);
    const patient =
      requestedPatientId === undefined
        ? patients[0]
        : patients.find(({ patientId }) => patientId === requestedPatientId);
    const files = patient
      ? await readPatientDailyFiles(packages, patient.patientId)
      : [];
    const wardName = packages.at(-1)?.manifest.ward_name ?? "";
    const items = buildRecordTimeline(files);
    return { ok: true, wardName, patients, patient, items };
  } catch (error) {
    return { ok: false, message: toLoadErrorMessage(error) };
  }
}
