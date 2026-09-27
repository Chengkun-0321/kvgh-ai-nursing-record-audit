import type { WardBedBoard } from "@/types/ward";

// 完全虛構的展示資料，不含任何真實病患資訊；訊息用語依 audit-rules.md「訊息用語」
export const MOCK_WARD_BED_BOARDS: Record<string, WardBedBoard> = {
  W51: {
    wardCode: "W51",
    wardName: "內科病房",
    businessDate: "2026-09-26",
    beds: [
      {
        bedCode: "W51-1",
        patient: {
          patientKey: "pk_0001",
          name: "陳冠宇",
          sex: "M",
          ageYears: 34,
          admissionDate: "2026-09-24",
          diagnosis: "急性闌尾炎術後",
        },
        findings: [],
      },
      {
        bedCode: "W51-2",
        patient: {
          patientKey: "pk_0002",
          name: "李玉華",
          sex: "F",
          ageYears: 72,
          admissionDate: "2026-09-18",
          diagnosis: "心衰竭",
        },
        findings: [
          {
            ruleCode: "R03",
            verdict: "ERROR",
            message: "入院護理評估未見必要項目：營養評估、心靈社會，請確認",
            recordedAt: "2026-09-26T08:00:00+08:00",
          },
          {
            ruleCode: "R01",
            verdict: "WARNING",
            message: "入院經過與身體評估的呼吸狀況描述不一致，請確認",
            recordedAt: "2026-09-26T12:30:00+08:00",
          },
        ],
      },
      {
        bedCode: "W51-3",
        patient: {
          patientKey: "pk_0003",
          name: "張志明",
          sex: "M",
          ageYears: 58,
          admissionDate: "2026-09-21",
          diagnosis: "第二型糖尿病",
        },
        findings: [],
      },
      {
        bedCode: "W51-4",
        patient: {
          patientKey: "pk_0004",
          name: "林佩君",
          sex: "F",
          ageYears: 29,
          admissionDate: "2026-09-25",
          diagnosis: "急性腎盂腎炎",
        },
        findings: [
          {
            ruleCode: "R02",
            verdict: "WARNING",
            message:
              "今日紀錄與前日高度相似，但生命徵象已有變化，請確認是否需更新",
            recordedAt: "2026-09-26T09:15:00+08:00",
          },
        ],
      },
      {
        bedCode: "W51-5",
        patient: {
          patientKey: "pk_0005",
          name: "黃秀英",
          sex: "F",
          ageYears: 67,
          admissionDate: "2026-09-20",
          diagnosis: "社區型肺炎",
        },
        findings: [],
      },
      {
        bedCode: "W51-6",
        patient: {
          patientKey: "pk_0006",
          name: "吳金水",
          sex: "M",
          ageYears: 81,
          admissionDate: "2026-09-15",
          diagnosis: "慢性阻塞性肺病急性惡化",
        },
        findings: [
          {
            ruleCode: "R03",
            verdict: "ERROR",
            message: "入院護理評估未見必要項目：日常生活型態，請確認",
            recordedAt: "2026-09-26T07:40:00+08:00",
          },
          {
            ruleCode: "R06",
            verdict: "WARNING",
            message: "今日有會診，過程紀錄中未見相應紀錄，請確認",
            recordedAt: "2026-09-26T11:20:00+08:00",
          },
          {
            ruleCode: "R07",
            verdict: "WARNING",
            message: "今日給予止痛藥物，過程紀錄中未見療效追蹤，請確認",
            recordedAt: "2026-09-26T14:10:00+08:00",
          },
        ],
      },
      {
        bedCode: "W51-7",
        patient: {
          patientKey: "pk_0007",
          name: "蔡淑芬",
          sex: "F",
          ageYears: 49,
          admissionDate: "2026-09-23",
          diagnosis: "蜂窩性組織炎",
        },
        findings: [
          {
            ruleCode: "R05",
            verdict: "NEEDS_REVIEW",
            message: "轉入摘要資料不足，系統無法判定，請人工確認",
            recordedAt: "2026-09-26T10:05:00+08:00",
          },
        ],
      },
      {
        bedCode: "W51-8",
        patient: {
          patientKey: "pk_0008",
          name: "劉正雄",
          sex: "M",
          ageYears: 76,
          admissionDate: "2026-09-19",
          diagnosis: "缺血性腦中風",
        },
        findings: [],
      },
      {
        bedCode: "W51-9",
        patient: {
          patientKey: "pk_0009",
          name: "許家豪",
          sex: "M",
          ageYears: 41,
          admissionDate: "2026-09-22",
          diagnosis: "上消化道出血",
        },
        findings: [
          {
            ruleCode: "R04",
            verdict: "WARNING",
            message: "今日身體評估有下肢水腫，過程紀錄中未見相應追蹤，請確認",
            recordedAt: "2026-09-26T13:45:00+08:00",
          },
        ],
      },
      {
        bedCode: "W51-10",
        patient: {
          patientKey: "pk_0010",
          name: "鄭雅婷",
          sex: "F",
          ageYears: 55,
          admissionDate: "2026-09-24",
          diagnosis: "急性膽囊炎",
        },
        findings: [],
      },
    ],
  },
};
