import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatNumber, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import ErrorBanner from "../../components/common/ErrorBanner";
import StatusBadge from "../../components/common/StatusBadge";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import TimesheetFormModal from "./TimesheetFormModal";

const STATUSES = ["draft", "submitted", "approved", "rejected"].map((v) => ({ value: v, label: titleCase(v) }));

function HoursTiles({ filters }) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v != null));
  const q = useQuery({
    queryKey: ["/timesheets/", "summary", params],
    queryFn: async () => unwrap(await api.get("/timesheets/summary/", { params })),
  });
  const hours = Object.fromEntries((q.data?.by_status ?? []).map((r) => [r.status, r.hours]));
  return (
    <div className="stage-tiles">
      {STATUSES.map((s) => (
        <div key={s.value} className="kpi"><span className="muted">{s.label}</span><strong>{formatNumber(hours[s.value] ?? 0)}</strong><small className="muted">hours</small></div>
      ))}
    </div>
  );
}

export default function TimesheetsPage() {
  const { user, hasRole } = useAuth();
  const qc = useQueryClient();
  const isReviewer = hasRole("project_manager");
  const canLog = user.roles.includes("employee") || user.roles.includes("project_manager");
  const list = usePaginatedList("/timesheets/", isReviewer ? { status: "submitted" } : {});
  const [editing, setEditing] = useState(null);        // null | "new" | timesheet
  const [rejecting, setRejecting] = useState(null);
  const act = useApiAction(
    async ({ id, verb, body }) => unwrap(await api.post(`/timesheets/${id}/${verb}/`, body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/timesheets/"] }) }
  );
  const run = (id, verb, body) => { act.reset(); return act.run({ id, verb, body }); };

  const columns = [
    { key: "work_date", header: "Date", render: (r) => formatDate(r.work_date) },
    { key: "employee_name", header: "Employee" },
    { key: "project_name", header: "Project" },
    { key: "task_title", header: "Task" },
    { key: "hours", header: "Hours", render: (r) => formatNumber(r.hours) },
    { key: "description", header: "Description", render: (r) => <span className="truncate">{r.description}</span> },
    { key: "status", header: "Status", render: (r) => (
      <div className="stack"><StatusBadge status={r.status} />{r.status === "rejected" && <small className="error-text">{r.rejection_reason}</small>}</div>
    ) },
    { key: "actions", header: "", render: (r) => (
      <div className="page-actions">
        {r.is_mine && ["draft", "rejected"].includes(r.status) && (
          <>
            <button className="btn btn-ghost" onClick={() => setEditing(r)}>Edit</button>
            <button className="btn btn-primary" disabled={act.busy} onClick={() => run(r.id, "submit")}>Submit</button>
          </>
        )}
        {isReviewer && r.status === "submitted" && !r.is_mine && (
          <>
            <button className="btn btn-primary" disabled={act.busy} onClick={() => run(r.id, "approve")}>Approve</button>
            <button className="btn btn-danger" onClick={() => { act.reset(); setRejecting(r); }}>Reject</button>
          </>
        )}
      </div>
    ) },
  ];

  return (
    <>
      <PageHeader title="Timesheets" subtitle={isReviewer ? "Review submitted hours and track your own" : "Log your hours and follow their approval"}
                  actions={canLog && <button className="btn btn-primary" onClick={() => setEditing("new")}>New timesheet</button>} />
      <HoursTiles filters={list.filters} />
      <ErrorBanner message={act.error?.message} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search description, employee, project…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={STATUSES} />
        <input className="input" type="date" aria-label="From date" value={list.filters.date_from ?? ""}
               onChange={(e) => list.setFilter("date_from", e.target.value)} />
        <input className="input" type="date" aria-label="To date" value={list.filters.date_to ?? ""}
               onChange={(e) => list.setFilter("date_to", e.target.value)} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 emptyTitle="No timesheets found" emptyHint={isReviewer ? "Nothing is waiting for review with these filters." : "Log your first day of work."}
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <TimesheetFormModal sheet={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog open={Boolean(rejecting)} title="Reject timesheet" danger requireReason confirmLabel="Reject"
                     message="Tell the employee what to correct. They can fix it and submit again."
                     busy={act.busy} error={act.error?.message} onCancel={() => setRejecting(null)}
                     onConfirm={async (reason) => { const r = await run(rejecting.id, "reject", { reason }); if (r.ok) setRejecting(null); }} />
    </>
  );
}
