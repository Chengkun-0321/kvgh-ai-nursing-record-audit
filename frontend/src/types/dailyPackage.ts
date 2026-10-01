// 院方每日資料包格式（不是後端 API，沒有 OpenAPI 可產生）；
// 欄位以 docs/hospital-data-spec/patient-daily.schema.json 為準，只列畫面會用到的部分

import type { Sex } from "./ward";

export type PatientStatus = "inpatient" | "transferred_out" | "discharged";

export type Shift = "day" | "evening" | "night";

export type ManifestPatient = {
  patient_id: string;
  file: string;
  bed_code: string;
  status: PatientStatus;
};

/** 每日資料包清單 `manifest.json`。 */
export type DailyManifest = {
  schema_version: string;
  ward_code: string;
  ward_name: string;
  business_date: string;
  patients: ManifestPatient[];
};

export type DailyPatient = {
  patient_id: string;
  bed_code: string;
  sex: Sex;
  age_years: number;
  admission_at: string;
  admission_diagnosis: string;
  status: PatientStatus;
};

type Consciousness = {
  scale: "GCS" | "RASS";
  e: string | null;
  v: string | null;
  m: string | null;
  rass: string | null;
};

type AbnormalStatus = {
  status: "正常" | "異常";
  abnormal_types: string[];
  other?: string | null;
};

type MusclePower = {
  left_upper: string | null;
  right_upper: string | null;
  left_lower: string | null;
  right_lower: string | null;
};

type FallRisk = {
  unable_to_move: boolean;
  risk_factors: string[];
  medications: string[];
  score: number;
  high_risk: boolean;
};

/** 身體評估各項目；空白項目為 `null`。 */
export type AssessmentItems = {
  consciousness: Consciousness | null;
  pain: { score: number | null; unable_to_assess: boolean } | null;
  sleep: string | null;
  airway: string | null;
  tubes: { has_tube: boolean; description: string | null } | null;
  pulse: AbnormalStatus | null;
  limb_circulation: string | null;
  breath_sounds: AbnormalStatus | null;
  cough: string | null;
  sore_throat: string | null;
  bowel_sounds: string | null;
  appetite: string[] | null;
  urination: AbnormalStatus | null;
  skin_pressure_prone_sites: string[] | null;
  muscle_power: MusclePower | null;
  mobility: string | null;
  fall_risk: FallRisk | null;
};

/** 入院評估中只看「有沒有」的區塊；內容欄位依院方畫面而異。 */
export type AdmissionSection = {
  completed: boolean;
  content: Record<string, unknown> | null;
};

export type AdmissionSections = {
  basic_info: AdmissionSection;
  personal_history: AdmissionSection;
  nutrition: AdmissionSection;
  daily_living: AdmissionSection;
  physical_assessment: {
    completed: boolean;
    content: { narrative: string | null; items: AssessmentItems } | null;
  };
  psychosocial: AdmissionSection;
  admission_course: { completed: boolean; content: { text: string } | null };
  environment: {
    completed: boolean;
    content: {
      introduced_items: string[];
      not_introduced: { item: string; reason: string }[];
    } | null;
  };
};

export type AdmissionSectionKey = keyof AdmissionSections;

export type AdmissionAssessment = {
  record_id: string;
  assessed_at: string;
  author_id: string;
  last_modified_at: string | null;
  sections: AdmissionSections;
};

export type DailyPhysicalAssessment = {
  record_id: string;
  assessed_at: string;
  shift: Shift;
  author_id: string;
  last_modified_at: string | null;
  items: AssessmentItems;
};

export type NursingProgressNote = {
  record_id: string;
  recorded_at: string;
  title_category: string;
  title: string;
  content: string;
  author_id: string;
  last_modified_at: string | null;
};

export type Transfer = {
  transfer_id: string;
  direction: "in" | "out";
  occurred_at: string;
  from_unit: string;
  to_unit: string;
  reason: string | null;
};

export type Consultation = {
  consultation_id: string;
  consultant_role: string;
  department: string;
  consult_type: string;
  ordered_at: string;
  signed_at: string | null;
  replied_at: string | null;
  status: string;
  condition_summary: string | null;
  reply_content: string | null;
};

export type MedicationAdministration = {
  administration_id: string;
  administered_at: string;
  administered_by: string;
  dose: number | null;
  unit: string | null;
  rate: string | null;
  status: string;
  remark: string | null;
};

export type MedicationOrder = {
  order_id: string;
  order_category: "常規" | "臨時";
  drug_name: string;
  route: string;
  dose: number;
  unit: string;
  frequency: string;
  is_high_alert: boolean;
  ordered_at: string;
  prescriber_id: string;
  status: string;
  administrations: MedicationAdministration[];
};

export type VitalSign = {
  record_id: string;
  measured_at: string;
  body_temperature: number | null;
  temperature_site: string | null;
  pulse: number | null;
  respiration: number | null;
  sbp: number | null;
  dbp: number | null;
  spo2: number | null;
  oxygen_therapy: string | null;
  measured_by: string;
};

export type LabResult = {
  record_id: string;
  item: string;
  value: string;
  unit: string | null;
  reference_range: string | null;
  abnormal_flag: "H" | "L" | null;
  collected_at: string;
  reported_at: string | null;
};

/** 一位病患一天的資料（`<YYYYMMDD>/<patient_id>.json`）。 */
export type PatientDailyFile = {
  schema_version: string;
  business_date: string;
  patient: DailyPatient;
  admission_assessment: AdmissionAssessment | null;
  daily_physical_assessments: DailyPhysicalAssessment[];
  nursing_progress_notes: NursingProgressNote[];
  transfers: Transfer[];
  consultations: Consultation[];
  medication_orders: MedicationOrder[];
  vital_signs: VitalSign[];
  lab_results: LabResult[];
};
