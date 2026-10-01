import type {
  AdmissionSectionKey,
  AssessmentItems,
} from "@/types/dailyPackage";

/** 空白項目（院方送 `null`）的顯示文字。 */
export const EMPTY_VALUE = "—";

export type LabeledValue = {
  key: string;
  label: string;
  value: string;
};

type AssessmentItemKey = keyof AssessmentItems;

type AbnormalStatus = NonNullable<AssessmentItems["pulse"]>;

// 項目名稱與順序照院內身評畫面
const ASSESSMENT_ITEMS: readonly { key: AssessmentItemKey; label: string }[] = [
  { key: "consciousness", label: "意識" },
  { key: "pain", label: "疼痛" },
  { key: "sleep", label: "睡眠" },
  { key: "airway", label: "氣管" },
  { key: "tubes", label: "管路" },
  { key: "pulse", label: "脈搏" },
  { key: "limb_circulation", label: "肢體循環" },
  { key: "breath_sounds", label: "呼吸音" },
  { key: "cough", label: "咳嗽" },
  { key: "sore_throat", label: "喉嚨痛" },
  { key: "bowel_sounds", label: "腸音" },
  { key: "appetite", label: "食慾" },
  { key: "urination", label: "泌尿" },
  { key: "skin_pressure_prone_sites", label: "皮膚：容易壓紅部位" },
  { key: "muscle_power", label: "肌肉力量" },
  { key: "mobility", label: "移動能力" },
  { key: "fall_risk", label: "跌倒危險" },
];

function joinList(values: readonly string[]): string {
  return values.length === 0 ? EMPTY_VALUE : values.join("、");
}

function formatAbnormalStatus(value: AbnormalStatus): string {
  if (value.status === "正常") {
    return "正常";
  }
  const details = [...value.abnormal_types, value.other ?? ""].filter(Boolean);
  return details.length === 0 ? "異常" : `異常：${details.join("、")}`;
}

function formatFallRisk(value: NonNullable<AssessmentItems["fall_risk"]>) {
  return [
    `${value.score} 分`,
    value.high_risk ? "高危險" : "",
    value.unable_to_move ? "無法移動" : "",
    value.risk_factors.join("、"),
    value.medications.join("、"),
  ]
    .filter(Boolean)
    .join("；");
}

const formatText = (value: string) => value;

// 只把院方的原值轉成可讀文字，不判斷正常或異常（判斷屬稽核規則）
const ITEM_FORMATTERS: {
  [K in AssessmentItemKey]: (value: NonNullable<AssessmentItems[K]>) => string;
} = {
  consciousness: (value) =>
    value.scale === "GCS"
      ? `GCS E${value.e ?? "-"}V${value.v ?? "-"}M${value.m ?? "-"}`
      : `RASS ${value.rass ?? "-"}`,
  pain: (value) =>
    value.unable_to_assess ? "無法評估" : `${value.score ?? EMPTY_VALUE} 分`,
  sleep: formatText,
  airway: formatText,
  tubes: (value) => (value.has_tube ? (value.description ?? "有") : "無"),
  pulse: formatAbnormalStatus,
  limb_circulation: formatText,
  breath_sounds: formatAbnormalStatus,
  cough: formatText,
  sore_throat: formatText,
  bowel_sounds: formatText,
  appetite: joinList,
  urination: formatAbnormalStatus,
  skin_pressure_prone_sites: joinList,
  muscle_power: (value) =>
    `左上 ${value.left_upper ?? "-"}／右上 ${value.right_upper ?? "-"}／左下 ${value.left_lower ?? "-"}／右下 ${value.right_lower ?? "-"}`,
  mobility: formatText,
  fall_risk: formatFallRisk,
};

function formatAssessmentItem<K extends AssessmentItemKey>(
  items: AssessmentItems,
  key: K,
): string {
  const value = items[key];
  if (value === null || value === undefined) {
    return EMPTY_VALUE;
  }
  return ITEM_FORMATTERS[key](value);
}

/** 身體評估全部項目，依院內畫面順序轉成「名稱＋值」。 */
export function describeAssessmentItems(
  items: AssessmentItems,
): LabeledValue[] {
  return ASSESSMENT_ITEMS.map(({ key, label }) => ({
    key,
    label,
    value: formatAssessmentItem(items, key),
  }));
}

/** 入院評估 8 大項，順序照院內畫面。 */
export const ADMISSION_SECTIONS: readonly {
  key: AdmissionSectionKey;
  label: string;
}[] = [
  { key: "basic_info", label: "基本資料" },
  { key: "personal_history", label: "個人病史" },
  { key: "nutrition", label: "營養評估" },
  { key: "daily_living", label: "日常生活型態" },
  { key: "physical_assessment", label: "身體評估" },
  { key: "psychosocial", label: "心靈社會" },
  { key: "admission_course", label: "住院經過" },
  { key: "environment", label: "環境" },
];

// 入院評估「有無」類區塊的欄位名稱；沒列到的欄位直接顯示英文鍵
const ADMISSION_FIELD_LABELS: Record<string, string> = {
  education: "教育程度",
  language: "語言",
  religion: "宗教",
  marital_status: "婚姻",
  occupation: "職業",
  primary_caregiver: "主要照顧者",
  admission_method: "入院方式",
  accompanied_by: "陪同者",
  past_history: "過去病史",
  surgical_history: "手術史",
  allergy: "過敏",
  blood_type: "血型",
  smoking: "吸菸",
  alcohol: "喝酒",
  home_medications: "居家用藥",
  height_cm: "身高（cm）",
  weight_kg: "體重（kg）",
  bmi: "BMI",
  diet: "飲食",
  chewing_swallowing: "咀嚼吞嚥",
  nutrition_screening_score: "營養篩檢分數",
  recent_intake: "近期進食",
  weight_change: "體重變化",
  adl_barthel: "ADL（巴氏量表）",
  bowel: "排便",
  urination: "排尿",
  sleep: "睡眠",
  exercise: "運動",
  bathing: "沐浴",
  mood: "情緒",
  coping: "因應方式",
  support_system: "支持系統",
  religion_support: "宗教支持",
};

/** 把區塊內容的任意值轉成一行文字（陣列以「、」連接，物件取各欄位值）。 */
export function formatContentValue(value: unknown): string {
  if (value === null || value === undefined) {
    return EMPTY_VALUE;
  }
  if (Array.isArray(value)) {
    return value.length === 0 ? "無" : value.map(formatContentValue).join("、");
  }
  if (typeof value === "object") {
    return Object.values(value).map(formatContentValue).join(" ");
  }
  return String(value);
}

/** 入院評估「有無」類區塊的內容，轉成「名稱＋值」清單。 */
export function describeSectionContent(
  content: Record<string, unknown>,
): LabeledValue[] {
  return Object.entries(content).map(([key, value]) => ({
    key,
    label: ADMISSION_FIELD_LABELS[key] ?? key,
    value: formatContentValue(value),
  }));
}
