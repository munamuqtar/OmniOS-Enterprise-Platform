import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDateTime, titleCase } from "../../utils/format";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";

const STAGES = ["applied", "screening", "interview", "evaluation", "offered", "hired", "rejected"];

export default function PipelineTab() {
  const navigate = useNavigate();
  const list = usePaginatedList("/recruitment-applications/");
  const vacancies = useQuery({
    queryKey: ["/vacancies/", "options"],
    queryFn: async () => unwrap(await api.get("/vacancies/")).results,
  });
  const vacancy = list.filters.vacancy ?? "";
  const summary = useQuery({
    queryKey: ["/recruitment-applications/", "summary", vacancy],
    queryFn: async () => unwrap(await api.get("/recruitment-applications/summary/", { params: vacancy ? { vacancy } : {} })),
  });
  const columns = [
    { key: "candidate_name", header: "Candidate" },
    { key: "vacancy_title", header: "Vacancy" },
    { key: "stage", header: "Stage", render: (r) => <StatusBadge status={r.stage} /> },
    { key: "interview_at", header: "Interview", render: (r) => (r.interview_at ? `${formatDateTime(r.interview_at)}${r.interview_location ? ` · ${r.interview_location}` : ""}` : "—") },
    { key: "created_at", header: "Applied", render: (r) => formatDateTime(r.created_at) },
  ];
  const activeStage = list.filters.stage ?? "";

  return (
    <>
      <div className="stage-tiles">
        {STAGES.map((s) => (
          <button key={s} className={`kpi tile-button ${activeStage === s ? "selected" : ""}`}
                  onClick={() => list.setFilter("stage", activeStage === s ? "" : s)}>
            <span className="muted">{titleCase(s)}</span>
            <strong>{summary.data?.[s] ?? 0}</strong>
          </button>
        ))}
      </div>
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search candidate or vacancy…" />
        <FilterSelect label="Vacancy" allLabel="All vacancies" value={vacancy}
                      onChange={(v) => list.setFilter("vacancy", v)}
                      options={(vacancies.data ?? []).map((v) => ({ value: v.id, label: v.title }))} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/hr/recruitment/applications/${r.id}`)}
                 emptyTitle="No applications" emptyHint="Register a candidate and apply them to an open vacancy."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
    </>
  );
}