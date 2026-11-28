import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/providers/auth-context";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import ProgressBar from "../../components/common/ProgressBar";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import ProjectFormModal from "./ProjectFormModal";

const STATUSES = ["draft", "planned", "active", "on_hold", "completed", "cancelled"].map((v) => ({ value: v, label: titleCase(v) }));

export default function ProjectsPage() {
  const { hasRole } = useAuth();
  const list = usePaginatedList("/projects/");
  const branches = useBranchOptions();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  const columns = [
    { key: "project_code", header: "Code" },
    { key: "name", header: "Project" },
    { key: "client_name", header: "Client" },
    { key: "manager_name", header: "Manager" },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "progress", header: "Progress", render: (r) => (
      <div className="progress-cell"><ProgressBar value={r.progress} /><span>{r.progress}%</span></div>
    ) },
    { key: "dates", header: "Dates", render: (r) => `${formatDate(r.start_date)} – ${formatDate(r.end_date)}` },
  ];

  return (
    <>
      <PageHeader title="Projects" subtitle="Delivery work for your clients"
                  actions={hasRole("project_manager") && <button className="btn btn-primary" onClick={() => setCreating(true)}>New project</button>} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name, code, client…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={STATUSES} />
        {branches.length > 1 && (
          <FilterSelect label="Branch" allLabel="All branches" value={list.filters.branch ?? ""}
                        onChange={(v) => list.setFilter("branch", v)}
                        options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        )}
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/projects/${r.id}`)}
                 emptyTitle="No projects found" emptyHint="Projects are created here or by converting an approved quotation."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {creating && <ProjectFormModal onClose={() => setCreating(false)}
                                     onSaved={(p) => { setCreating(false); navigate(`/projects/${p.id}`); }} />}
    </>
  );
}
