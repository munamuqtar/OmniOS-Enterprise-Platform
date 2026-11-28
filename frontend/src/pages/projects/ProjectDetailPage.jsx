import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatMoney, titleCase } from "../../utils/format";
import { PROJECT_NEXT } from "../../utils/workflow";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import ProgressBar from "../../components/common/ProgressBar";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import DataTable from "../../components/tables/DataTable";
import { LookupField, TextField } from "../../components/forms/fields";
import ProjectFormModal from "./ProjectFormModal";
import TaskFormModal from "./TaskFormModal";
import TaskStatusButtons from "./TaskStatusButtons";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const project = useDetail("/projects/", id);
  const members = useDetail("/projects/", id, "members/");
  const report = useDetail("/projects/", id, "report/");
  const tasks = usePaginatedList("/tasks/", { project: id });
  const [dialog, setDialog] = useState(null);            // "edit" | "task" | a task object
  const [confirmStatus, setConfirmStatus] = useState(null);
  const memberForm = useFormState({ employee: "", role: "" });
  const refresh = () => qc.invalidateQueries({ queryKey: ["/projects/"] });
  const move = useApiAction(async (status) => unwrap(await api.post(`/projects/${id}/status/`, { status })), { onSuccess: refresh });
  const addMember = useApiAction(async (body) => unwrap(await api.post(`/projects/${id}/members/`, body)), { onSuccess: refresh });
  const removeMember = useApiAction(async (employee) => unwrap(await api.post(`/projects/${id}/members/remove/`, { employee })), { onSuccess: refresh });

  if (project.isLoading) return <Spinner />;
  if (project.error) return <ErrorBanner message={parseApiError(project.error).message} onRetry={project.refetch} />;
  const p = project.data;
  const canManage = hasRole("project_manager");
  const closed = ["completed", "cancelled"].includes(p.status);

  async function add(e) {
    e.preventDefault();
    const r = await addMember.run({ employee: memberForm.values.employee, role: memberForm.values.role });
    if (r.ok) memberForm.reset(); else memberForm.setErrors(r.error.fields);
  }

  const taskColumns = [
    { key: "title", header: "Task" },
    { key: "assignee_name", header: "Assignee" },
    { key: "due_date", header: "Due", render: (r) => <>{formatDate(r.due_date)} {r.is_overdue && <span className="badge red">Overdue</span>}</> },
    { key: "priority", header: "Priority", render: (r) => <StatusBadge status={r.priority} /> },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "actions", header: "", render: (r) => <TaskStatusButtons task={r} /> },
  ];

  return (
    <>
      <PageHeader title={<>{p.name} <StatusBadge status={p.status} /></>} subtitle={`${p.project_code} · ${p.client_name}`}
        actions={
          <>
            <Link className="btn btn-ghost" to="/projects">Back</Link>
            {canManage && !closed && <button className="btn btn-ghost" onClick={() => setDialog("edit")}>Edit</button>}
            {canManage && PROJECT_NEXT[p.status].map((s) => (
              <button key={s} className={`btn ${s === "cancelled" ? "btn-danger" : "btn-primary"}`} disabled={move.busy}
                      onClick={() => setConfirmStatus(s)}>{titleCase(s)}</button>
            ))}
          </>
        } />
      <ErrorBanner message={move.error?.message} />

      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Manager", p.manager_name], ["Start", formatDate(p.start_date)],
            ["End", formatDate(p.end_date)], ["Budget", p.budget ? formatMoney(p.budget) : null], ["Description", p.description || null]]} />
          <h3 className="space-top">Progress</h3>
          <ProgressBar value={p.progress} />
          <small className="muted">{p.completed_count} of {p.task_count} tasks completed</small>
        </section>
        <section className="card">
          <h3>Report</h3>
          {report.data ? (
            <InfoGrid items={[["Members", report.data.members], ["Tasks", report.data.tasks_total],
              ["Overdue tasks", report.data.overdue_tasks],
              ...Object.entries(report.data.tasks_by_status).map(([s, n]) => [titleCase(s), n])]} />
          ) : <Spinner />}
        </section>
        <section className="card">
          <h3>Team</h3>
          {canManage && !closed && (
            <form onSubmit={add} className="inline-form">
              <ErrorBanner message={addMember.error?.message} />
              <LookupField form={memberForm} name="employee" label="Employee" endpoint="/employees/" required
                           params={{ branch: p.branch, status: "active" }}
                           labelOf={(e) => `${e.first_name} ${e.last_name} (${e.employee_number})`} />
              <TextField form={memberForm} name="role" label="Role on project" />
              <button className="btn btn-primary" disabled={addMember.busy}>Add member</button>
            </form>
          )}
          <ErrorBanner message={removeMember.error?.message} />
          {members.data?.length ? (
            <ul className="activity">
              {members.data.map((m) => (
                <li key={m.id}>
                  <strong>{m.employee_name}</strong> · {m.employee_number}{m.role && ` · ${m.role}`}
                  {canManage && !closed && (
                    <button className="link" onClick={() => removeMember.run(m.employee)}> Remove</button>
                  )}
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No members yet" hint="Add employees before assigning tasks." />}
        </section>
      </div>

      <section className="card panel-gap">
        <div className="page-header">
          <h3>Tasks</h3>
          {canManage && !closed && <button className="btn btn-primary" onClick={() => setDialog("task")}>New task</button>}
        </div>
        <DataTable columns={taskColumns} rows={tasks.rows} loading={tasks.isLoading}
                   error={tasks.error && parseApiError(tasks.error).message} onRetry={tasks.refetch}
                   onRowClick={canManage ? (t) => setDialog(t) : undefined}
                   emptyTitle="No tasks yet"
                   pagination={{ page: tasks.page, pageSize: tasks.pageSize, count: tasks.count, onPage: tasks.setPage }} />
      </section>

      {dialog === "edit" && <ProjectFormModal project={p} onClose={() => setDialog(null)} onSaved={() => setDialog(null)} />}
      {dialog === "task" && <TaskFormModal projectId={id} onClose={() => setDialog(null)} />}
      {dialog && typeof dialog === "object" && <TaskFormModal task={dialog} onClose={() => setDialog(null)} />}
      <ConfirmDialog open={Boolean(confirmStatus)} danger={confirmStatus === "cancelled"} busy={move.busy}
                     title="Change project status" confirmLabel={confirmStatus ? titleCase(confirmStatus) : ""}
                     message={`Change the status of ${p.name} to ${confirmStatus ? titleCase(confirmStatus) : ""}?`}
                     onCancel={() => setConfirmStatus(null)}
                     onConfirm={async () => { await move.run(confirmStatus); setConfirmStatus(null); }} />
    </>
  );
}
