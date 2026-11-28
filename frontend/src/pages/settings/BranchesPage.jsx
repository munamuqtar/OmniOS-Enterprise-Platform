import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import FormDialog from "../../components/modals/FormDialog";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const STATUSES = [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }];

function BranchForm({ branch, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({
    name: branch?.name ?? "", branch_code: branch?.branch_code ?? "", address: branch?.address ?? "",
    phone: branch?.phone ?? "", email: branch?.email ?? "", manager: branch?.manager ?? "", status: branch?.status ?? "active",
  });
  const save = useApiAction(
    async (body) => unwrap(branch ? await api.put(`/branches/${branch.id}/`, body) : await api.post("/branches/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/branches/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const r = await save.run({ ...form.values, manager: form.values.manager || null });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={branch ? "Edit branch" : "New branch"} formId="branch-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save branch">
      <form id="branch-form" onSubmit={submit}>
        <TextField form={form} name="name" label="Branch name" required />
        <TextField form={form} name="branch_code" label="Branch code" required hint="Short and unique, for example HQ." />
        <TextAreaField form={form} name="address" label="Address" rows={2} />
        <TextField form={form} name="phone" label="Phone" />
        <TextField form={form} name="email" label="Email" type="email" />
        <LookupField form={form} name="manager" label="Branch manager" endpoint="/lookups/users/" params={{ role: "sales" }}
                     labelOf={(u) => u.name} initialLabel={branch?.manager_name}
                     hint="The branch manager approves quotations for this branch, so pick a Sales user." />
        <SelectField form={form} name="status" label="Status" options={STATUSES} required />
      </form>
    </FormDialog>
  );
}

export default function BranchesPage() {
  const list = usePaginatedList("/branches/");
  const [editing, setEditing] = useState(null);          // null | "new" | branch
  const columns = [
    { key: "branch_code", header: "Code" },
    { key: "name", header: "Branch" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    { key: "manager_name", header: "Manager" },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
  ];
  return (
    <>
      <PageHeader title="Branches" subtitle="Each branch has its own isolated records"
                  actions={<button className="btn btn-primary" onClick={() => setEditing("new")}>New branch</button>} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name or code…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={STATUSES} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => setEditing(r)} emptyTitle="No branches yet" emptyHint="Create the organization first, then add branches."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <BranchForm branch={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}