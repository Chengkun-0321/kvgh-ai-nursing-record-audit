"use client";

import { useState } from "react";

import { useAuditRuns } from "@/hooks/useAuditRuns";
import type { PatientAuditDay } from "@/lib/api/patientAudits";

import { AuditResultDialog } from "./AuditResultDialog";
import { AuditRuleList } from "./AuditRuleList";
import { DateSwitcher } from "./DateSwitcher";
import { PatientAuditHeader } from "./PatientAuditHeader";
import { PatientAuditTitle } from "./PatientAuditTitle";
import { RunAllButton } from "./RunAllButton";

type PatientAuditBoardProps = {
  day: PatientAuditDay;
};

/**
 * 病患稽核頁的內容：頁首（含日期切換與一鍵稽核）、各項稽核、結果視窗。
 * 一鍵稽核與各項稽核共用同一份執行狀態，所以頁首由這裡渲染。父層以日期為 key，切換日期即重置。
 */
export function PatientAuditBoard({ day }: PatientAuditBoardProps) {
  const { rules, runRule, runAll, canRunAll, isRunningAll } = useAuditRuns(day);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const selected = rules.find((rule) => rule.rule_code === selectedCode);

  return (
    <>
      <PatientAuditHeader
        patientKey={day.patient_key}
        actions={
          <RunAllButton
            canRunAll={canRunAll}
            isRunning={isRunningAll}
            onRunAll={() => void runAll()}
          />
        }
      >
        <DateSwitcher
          patientKey={day.patient_key}
          businessDate={day.business_date}
          previousDate={day.previous_date}
          nextDate={day.next_date}
        />
      </PatientAuditHeader>
      <section
        aria-label="稽核總覽"
        className="rounded-panel bg-surface p-5 shadow-card lg:p-8"
      >
        <AuditRuleList
          title={<PatientAuditTitle day={day} />}
          rules={rules}
          pageDate={day.business_date}
          onOpen={setSelectedCode}
          onRun={(ruleCode) => void runRule(ruleCode)}
        />
      </section>
      <AuditResultDialog
        rule={selected}
        onClose={() => setSelectedCode(null)}
      />
    </>
  );
}
