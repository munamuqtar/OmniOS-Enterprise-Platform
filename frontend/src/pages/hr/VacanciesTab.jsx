import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useDepartments } from "../../hooks/useDepartments";
import { useFormState } from "../../hooks/useFormState";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import FormDialog from "../../components/modals/FormDialog";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import { SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const STATUSES = [{ value: "draft", label: "Draft" }, { value: "open", label: "Open" }, { value: "closed", label: "Closed" }];

function VacancyForm({ vacancy, onClose }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const departments = useDepartments();
  const form = useFormState({
    title: vacancy?.title ?? "", department: vacancy?.department ?? "", description: vacancy?.description ?? "",
    branch: vacancy?.branch ?? (branches.length === 1 ? branches[0].id : ""), openings: vacancy?.openings ?? 1,
    status: vacancy?.status ?? "open", closing_date: vacancy?.closing_date ?? "",
  });
  const save = useApiAction(
    async (body) => unwrap(vacancy ? await api.put(`/vacancies/${vacancy.id}/`, body) : await api.post("/vacancies/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/vacancies/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const r = await save.run({ ...v, department: v.department || null, closing_date: v.closing_date || null });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={vacancy ? "Edit vacancy" : "New vacancy"} formId="vacancy-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save vacancy">
      <form id="vacancy-form" onSubmit={submit}>
        <TextField form={form} name="title" label="Job title" required />
        <SelectField form={form} name="department" label="Department" options={departments.map((d) => ({ value: d.id, label: d.name }))} />
        <SelectField form={form} name="branch" label="Branch" required options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <TextAreaField form={form} name="description" label="Description" rows={4} />
        <TextField form={form} name="openings" label="Openings" type="number" min="1" required />
        <SelectField form={form} name="status" label="Status" options={STATUSES} required hint="Only open vacancies accept applications." />
        <TextField form={form} name="closing_date" label="Closing date" type="date" />
      </form>
    </FormDialog>
  );
}

export default function VacanciesTab() {
  const list = usePaginatedList("/vacancies/");
  const [editing, setEditing] = useState(null);         // null | "new" | vacancy
  const columns = [
    { key: "title", header: "Vacancy" },
    { key: "department_name", header: "Department" },
    { key: "branch_name", header: "Branch" },
    { key: "openings", header: "Openings" },
    { key: "closing_date", header: "Closes", render: (r) => formatDate(r.closing_date) },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
  ];
  return (
    <>
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search vacancies…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={STATUSES} />
        <button className="btn btn-primary" onClick={() => setEditing("new")}>New vacancy</button>
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => setEditing(r)} emptyTitle="No vacancies yet" emptyHint="Open a vacancy to start receiving applications."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <VacancyForm vacancy={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}