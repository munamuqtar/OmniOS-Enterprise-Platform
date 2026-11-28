import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { parseApiError } from "../../utils/errors";
import { formatDate, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import LeadFormModal from "./LeadFormModal";

const LEAD_STATUSES = ["new", "contacted", "pending", "qualified", "unqualified", "converted"]
  .map((value) => ({ value, label: titleCase(value) }));

export default function LeadsPage() {
  const list = usePaginatedList("/leads/");
  const branches = useBranchOptions();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  const columns = [
    { key: "name", header: "Name" },
    { key: "company_name", header: "Company" },
    { key: "email", header: "Email" },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "owner_name", header: "Salesperson" },
    { key: "branch_name", header: "Branch" },
    { key: "created_at", header: "Created", render: (r) => formatDate(r.created_at) },
  ];

  return (
    <>
      <PageHeader title="Leads" subtitle="Capture, qualify and convert prospects"
                  actions={<button className="btn btn-primary" onClick={() => setCreating(true)}>New lead</button>} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name, company, email…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={LEAD_STATUSES} />
        {branches.length > 1 && (
          <FilterSelect label="Branch" allLabel="All branches" value={list.filters.branch ?? ""}
                        onChange={(v) => list.setFilter("branch", v)}
                        options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        )}
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/crm/leads/${r.id}`)}
                 emptyTitle="No leads found" emptyHint="Create a lead or adjust the filters."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {creating && <LeadFormModal onClose={() => setCreating(false)}
                                  onSaved={(lead) => { setCreating(false); navigate(`/crm/leads/${lead.id}`); }} />}
    </>
  );
}