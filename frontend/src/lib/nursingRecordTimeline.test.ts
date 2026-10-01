import { describe, expect, it } from "vitest";

import type {
  Consultation,
  MedicationOrder,
  NursingProgressNote,
  PatientDailyFile,
} from "@/types/dailyPackage";

import {
  buildRecordTimeline,
  countByRecordType,
  filterTimeline,
  groupTimelineByDate,
} from "./nursingRecordTimeline";

// 完全虛構的最小資料，只填時間軸會用到的欄位
function dailyFile(
  businessDate: string,
  blocks: Partial<PatientDailyFile> = {},
): PatientDailyFile {
  return {
    schema_version: "0.1.0",
    business_date: businessDate,
    patient: {
      patient_id: "P001",
      bed_code: "W51-1",
      sex: "M",
      age_years: 70,
      admission_at: "2026-09-01T10:00:00+08:00",
      admission_diagnosis: "測試診斷",
      status: "inpatient",
    },
    admission_assessment: null,
    daily_physical_assessments: [],
    nursing_progress_notes: [],
    transfers: [],
    consultations: [],
    medication_orders: [],
    vital_signs: [],
    lab_results: [],
    ...blocks,
  };
}

function note(
  recordId: string,
  recordedAt: string,
  overrides: Partial<NursingProgressNote> = {},
): NursingProgressNote {
  return {
    record_id: recordId,
    recorded_at: recordedAt,
    title_category: "健康問題",
    title: "健康問題 ：測試",
    content: "內容",
    author_id: "N101",
    last_modified_at: null,
    ...overrides,
  };
}

function order(administrationIds: readonly string[]): MedicationOrder {
  return {
    order_id: "MED-001",
    order_category: "常規",
    drug_name: "Heparin",
    route: "IV",
    dose: 1000,
    unit: "U",
    frequency: "CONT",
    is_high_alert: true,
    ordered_at: "2026-09-01T09:00:00+08:00",
    prescriber_id: "D201",
    status: "執行中",
    administrations: administrationIds.map((id, index) => ({
      administration_id: id,
      administered_at: `2026-09-0${index + 1}T10:00:00+08:00`,
      administered_by: "N101",
      dose: 1000,
      unit: "U",
      rate: null,
      status: "已執行",
      remark: null,
    })),
  };
}

function consultation(overrides: Partial<Consultation>): Consultation {
  return {
    consultation_id: "CON-001",
    consultant_role: "醫師",
    department: "心臟外科",
    consult_type: "REGULAR",
    ordered_at: "2026-09-01T15:00:00+08:00",
    signed_at: null,
    replied_at: null,
    status: "未簽收",
    condition_summary: null,
    reply_content: null,
    ...overrides,
  };
}

// buildRecordTimeline 各情境各自一個 it（lib 目錄限制函式長度）
it("buildRecordTimeline：依時間由新到舊排序，跨日也正確", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-01", {
      nursing_progress_notes: [
        note("N-1", "2026-09-01T08:00:00+08:00"),
        note("N-2", "2026-09-01T20:00:00+08:00"),
      ],
    }),
    dailyFile("2026-09-02", {
      nursing_progress_notes: [note("N-3", "2026-09-02T09:00:00+08:00")],
    }),
  ]);

  expect(items.map((item) => item.key)).toEqual([
    "npn:N-3",
    "npn:N-2",
    "npn:N-1",
  ]);
});

it("buildRecordTimeline：轉入／轉出摘要與轉床事件歸在轉入轉出，其他過程紀錄歸在護理紀錄", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-12", {
      nursing_progress_notes: [
        note("N-1", "2026-09-12T10:00:00+08:00"),
        note("N-2", "2026-09-12T16:00:00+08:00", {
          title_category: "轉出摘要",
        }),
      ],
      transfers: [
        {
          transfer_id: "TRF-1",
          direction: "out",
          occurred_at: "2026-09-12T16:30:00+08:00",
          from_unit: "W51",
          to_unit: "MICU",
          reason: null,
        },
      ],
    }),
  ]);

  expect(items.map((item) => [item.key, item.recordType])).toEqual([
    ["trf:TRF-1", "transfer"],
    ["npn:N-2", "transfer"],
    ["npn:N-1", "nursing_progress_note"],
  ]);
});

it("buildRecordTimeline：同一張藥囑跨日出現時只保留一份藥囑，並列出每一次給藥", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-01", { medication_orders: [order(["MAR-1"])] }),
    dailyFile("2026-09-02", {
      medication_orders: [order(["MAR-1", "MAR-2"])],
    }),
    dailyFile("2026-09-03", {
      medication_orders: [order(["MAR-1", "MAR-2", "MAR-3"])],
    }),
  ]);

  expect(items.map((item) => item.key)).toEqual([
    "mar:MAR-3",
    "mar:MAR-2",
    "mar:MAR-1",
  ]);
});

it("buildRecordTimeline：沒有給藥的藥囑放在開立時間", () => {
  const [item] = buildRecordTimeline([
    dailyFile("2026-09-01", { medication_orders: [order([])] }),
  ]);

  expect(item).toMatchObject({
    key: "med:MED-001",
    occurredAt: "2026-09-01T09:00:00+08:00",
    administration: null,
  });
});

it("buildRecordTimeline：會診只保留最新狀態，放在回覆時間", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-02", { consultations: [consultation({})] }),
    dailyFile("2026-09-03", {
      consultations: [
        consultation({
          signed_at: "2026-09-03T09:00:00+08:00",
          replied_at: "2026-09-03T11:40:00+08:00",
          status: "已回覆",
        }),
      ],
    }),
  ]);

  expect(items).toHaveLength(1);
  expect(items[0]?.occurredAt).toBe("2026-09-03T11:40:00+08:00");
});

it("buildRecordTimeline：修改過的紀錄（同一 ID 再出現）以最後的版本為準", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-01", {
      nursing_progress_notes: [note("N-1", "2026-09-01T08:00:00+08:00")],
    }),
    dailyFile("2026-09-02", {
      nursing_progress_notes: [
        note("N-1", "2026-09-01T08:00:00+08:00", { content: "修改後" }),
      ],
    }),
  ]);

  expect(items).toHaveLength(1);
  expect(items[0]).toMatchObject({ record: { content: "修改後" } });
});

describe("groupTimelineByDate", () => {
  it("依紀錄時間的日期分組", () => {
    const items = buildRecordTimeline([
      dailyFile("2026-09-01", {
        nursing_progress_notes: [
          note("N-1", "2026-09-01T08:00:00+08:00"),
          note("N-2", "2026-09-01T23:30:00+08:00"),
        ],
      }),
      dailyFile("2026-09-02", {
        nursing_progress_notes: [note("N-3", "2026-09-02T00:30:00+08:00")],
      }),
    ]);

    expect(
      groupTimelineByDate(items).map(({ date, items: dayItems }) => [
        date,
        dayItems.length,
      ]),
    ).toEqual([
      ["2026-09-02", 1],
      ["2026-09-01", 2],
    ]);
  });
});

describe("countByRecordType / filterTimeline", () => {
  const items = buildRecordTimeline([
    dailyFile("2026-09-01", {
      nursing_progress_notes: [
        note("N-1", "2026-09-01T08:00:00+08:00"),
        note("N-2", "2026-09-01T09:00:00+08:00", {
          title_category: "轉入摘要",
        }),
      ],
      medication_orders: [order(["MAR-1"])],
    }),
  ]);

  it("計算各類型筆數，沒有資料的類型為 0", () => {
    expect(countByRecordType(items)).toMatchObject({
      nursing_progress_note: 1,
      transfer: 1,
      medication_administration: 1,
      vital_sign: 0,
    });
  });

  it("只保留勾選的類型", () => {
    const filtered = filterTimeline(items, new Set(["transfer"]));

    expect(filtered.map((item) => item.key)).toEqual(["npn:N-2"]);
  });
});
