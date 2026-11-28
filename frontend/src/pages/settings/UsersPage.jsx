import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import FormDialog from "../../components/modals/FormDialog";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import { CheckboxGroup, TextField } from "../../components/forms/fields";

function useRoleOptions() {
  const q = useQuery({ queryKey: ["/roles/", "options"], queryFn: async () => unwrap(await api.get("/roles/")).results });
  return (q.data ?? []).map((r) => ({ value: r.code, label: r.name }));
}

function UserForm({ account, onClose }) {
  const qc = useQueryClient();
  const roleOptions = useRoleOptions();
  const branches = useBranchOptions();
  const form = useFormState({
    username: account?.username ?? "", email: account?.email ?? "", first_name: account?.first_name ?? "",
    last_name: account?.last_name ?? "", password: "", is_active: account?.is_active ?? true,
    role_codes: account?.roles ?? [], branch_ids: account?.branches?.map((b) => b.id) ?? [],
  });
  const save = useApiAction(
    async (body) => unwrap(account ? await api.put(`/users/${account.id}/`, body) : await api.post("/users/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/users/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const { password, ...rest } = form.values;
    const r = await save.run(password ? { ...rest, password } : rest);
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={account ? `Edit ${account.username}` : "New user"} formId="user-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save user">
      <form id="user-form" onSubmit={submit}>
        <TextField form={form} name="username" label="Username" required autoComplete="off" />
        <TextField form={form} name="email" label="Email" type="email" required />
        <TextField form={form} name="first_name" label="First name" />
        <TextField form={form} name="last_name" label="Last name" />
        <TextField form={form} name="password" label="Password" type="password" autoComplete="new-password"
                   required={!account} hint={account ? "Leave empty to keep the current password." : "At least 10 characters, not a common password."} />
        <CheckboxGroup form={form} name="role_codes" label="Roles" options={roleOptions} hint="Roles decide what the person can see and do." />
        <CheckboxGroup form={form} name="branch_ids" label="Branch access" options={branches.map((b) => ({ value: b.id, label: b.name }))}
                       hint="The person can only see records of these branches." />
        {account && (
          <label className="check">
            <input type="checkbox" checked={form.values.is_active} onChange={(e) => form.set("is_active", e.target.checked)} /> Account is active
          </label>
        )}
      </form>
    </FormDialog>
  );
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const list = usePaginatedList("/users/");
  const roleOptions = useRoleOptions();
  const [editing, setEditing] = useState(null);          // null | "new" | user
  const [toggling, setToggling] = useState(null);
  const toggle = useApiAction(
    async (u) => unwrap(await api.put(`/users/${u.id}/`, { username: u.username, email: u.email, first_name: u.first_name,
                                                          last_name: u.last_name, is_active: !u.is_active })),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/users/"] }) }
  );

  const columns = [
    { key: "username", header: "Username" },
    { key: "name", header: "Name", render: (r) => `${r.first_name} ${r.last_name}`.trim() || "—" },
    { key: "email", header: "Email" },
    { key: "roles", header: "Roles", render: (r) => r.roles.map(titleCase).join(", ") || "—" },
    { key: "branches", header: "Branches", render: (r) => r.branches.map((b) => b.name).join(", ") || "—" },
    { key: "is_active", header: "Status", render: (r) => <StatusBadge status={r.is_active ? "active" : "inactive"} /> },
    { key: "actions", header: "", render: (r) => (
      <div className="page-actions">
        <button className="btn btn-ghost" onClick={(e) => { e.stopPropagation(); setEditing(r); }}>Edit</button>
        {r.id !== me.id && (
          <button className={`btn ${r.is_active ? "btn-danger" : "btn-primary"}`}
                  onClick={(e) => { e.stopPropagation(); toggle.reset(); setToggling(r); }}>
            {r.is_active ? "Deactivate" : "Activate"}
          </button>
        )}
      </div>
    ) },
  ];

  return (
    <>
      <PageHeader title="Users" subtitle="Provision accounts, roles and branch access"
                  actions={<button className="btn btn-primary" onClick={() => setEditing("new")}>New user</button>} />
      <ErrorBanner message={toggle.error?.message} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search username, name, email…" />
        <FilterSelect label="Status" allLabel="All accounts" value={list.filters.is_active ?? ""}
                      onChange={(v) => list.setFilter("is_active", v)}
                      options={[{ value: "true", label: "Active" }, { value: "false", label: "Inactive" }]} />
        <FilterSelect label="Role" allLabel="All roles" value={list.filters.roles__code ?? ""}
                      onChange={(v) => list.setFilter("roles__code", v)} options={roleOptions} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 emptyTitle="No users found"
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <UserForm account={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog open={Boolean(toggling)} danger={toggling?.is_active} busy={toggle.busy}
                     title={toggling?.is_active ? "Deactivate account" : "Activate account"}
                     confirmLabel={toggling?.is_active ? "Deactivate" : "Activate"}
                     message={toggling?.is_active
                       ? `${toggling?.username} will be signed out and will not be able to log in again until you reactivate the account.`
                       : `${toggling?.username} will be able to log in again.`}
                     onCancel={() => setToggling(null)}
                     onConfirm={async () => { const r = await toggle.run(toggling); if (r.ok) setToggling(null); }} />
    </>
  );
}