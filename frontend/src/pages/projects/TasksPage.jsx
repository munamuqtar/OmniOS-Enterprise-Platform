import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/providers/auth-context";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import TaskFormModal from "./TaskFormModal";
import TaskStatusButtons from "./TaskStatusButtons";

const opts = (list) => list.map((v) => ({ value: v, label: titleCase(v) }));

export default function TasksPage() {
  const { hasRole } = useAuth();
  const canManage = hasRole("project_manager");
  const list = usePaginatedList("/tasks/");
  const [editing, setEditing] = useState(null);       // null | "new" | task

  const columns = [
    { key: "title", header: "Task" },
    { key: "project_name", header: "Project", render: (r) => <Link to={`/projects/${r.project}`} onClick={(e) => e.stopPropagation()}>{r.project_name}</Link> },
    { key: "assignee_name", header: "Assignee" },
    { key: "due_date", header: "Due", render: (r) => <>{formatDate(r.due_date)} {r.is_overdue && <span className="badge red">Overdue</span>}</> },
    { key: "priority", header: "Priority", render: (r) => <StatusBadge status={r.priority} /> },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "actions", header: "", render: (r) => <TaskStatusButtons task={r} /> },
  ];

  return (
    <>
      <PageHeader title="Tasks" subtitle={canManage ? "Everything assigned across your projects" : "Work assigned to you"}
                  actions={canManage && <button className="btn btn-primary" onClick={() => setEditing("new")}>New task</button>} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search tasks or projects…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={opts(["todo", "in_progress", "review", "completed"])} />
        <FilterSelect label="Priority" allLabel="All priorities" value={list.filters.priority ?? ""}
                      onChange={(v) => list.setFilter("priority", v)} options={opts(["low", "medium", "high", "urgent"])} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={canManage ? (t) => setEditing(t) : undefined}
                 emptyTitle="No tasks found" emptyHint="Tasks appear here once a project manager assigns them."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <TaskFormModal task={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}
