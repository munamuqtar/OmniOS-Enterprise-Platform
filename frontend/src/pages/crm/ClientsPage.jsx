import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/providers/auth-context";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { parseApiError } from "../../utils/errors";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import ClientFormModal from "./ClientFormModal";

export default function ClientsPage() {
  const { hasRole } = useAuth();
  const list = usePaginatedList("/clients/");
  const branches = useBranchOptions();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const canWrite = hasRole("sales");

  const columns = [
    { key: "name", header: "Client" },
    { key: "company_name", header: "Company" },
    { key: "contact_person", header: "Contact" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "branch_name", header: "Branch" },
  ];

  return (
    <>
      <PageHeader title="Clients" subtitle="Customers and their history"
                  actions={canWrite && <button className="btn btn-primary" onClick={() => setCreating(true)}>New client</button>} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name, company, email…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)}
                      options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
        {branches.length > 1 && (
          <FilterSelect label="Branch" allLabel="All branches" value={list.filters.branch ?? ""}
                        onChange={(v) => list.setFilter("branch", v)}
                        options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        )}
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/crm/clients/${r.id}`)}
                 emptyTitle="No clients found" emptyHint="Clients appear here when leads are converted or created directly."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {creating && <ClientFormModal onClose={() => setCreating(false)}
                                    onSaved={(c) => { setCreating(false); navigate(`/crm/clients/${c.id}`); }} />}
    </>
  );
}