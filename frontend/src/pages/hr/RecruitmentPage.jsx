import { useState } from "react";
import PageHeader from "../../components/common/PageHeader";
import PipelineTab from "./PipelineTab";
import VacanciesTab from "./VacanciesTab";
import CandidatesTab from "./CandidatesTab";

const TABS = [["pipeline", "Pipeline"], ["vacancies", "Vacancies"], ["candidates", "Candidates"]];

export default function RecruitmentPage() {
  const [tab, setTab] = useState("pipeline");
  return (
    <>
      <PageHeader title="Recruitment" subtitle="Vacancies, candidates and the hiring pipeline" />
      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} className={`tab ${tab === key ? "active" : ""}`}
                  onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>
      {tab === "pipeline" && <PipelineTab />}
      {tab === "vacancies" && <VacanciesTab />}
      {tab === "candidates" && <CandidatesTab />}
    </>
  );
}