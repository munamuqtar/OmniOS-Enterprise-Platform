import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatMoney, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";

const STATUSES = ["draft", "pending_approval", "approved", "rejected"].map((value) => ({ value, label: titleCase(value) }));

function ApprovalPanel() {
  const { user } = useAuth();
  const q = useQuery({
    queryKey: ["/quotes/", "pending"], refetchInterval: 30000,
    queryFn: async () => unwrap(await api.get("/quotes/pending-approval/")),
  });
  const rows = (q.data ?? []).filter((x) => x.created_by !== user.id);
  if (!rows.length) return null;
  return (
    <section className="card panel-gap">
      <h3>Awaiting approval ({rows.length})</h3>
      <ul className="activity">
        {rows.map((x) => (
          <li key={x.id}>
            <Link to={`/sales/quotations/${x.id}`}><strong>{x.quote_number}</strong></Link> · {x.client_name || x.lead_name} · {formatMoney(x.total, x.currency)}
            <small className="muted">Submitted by {x.created_by_name}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function QuotationsPage() {
  const { hasRole } = useAuth();
  const list = usePaginatedList("/quotes/");
  const branches = useBranchOptions();
  const navigate = useNavigate();
  const canWrite = hasRole("sales");

  const columns = [
    { key: "quote_number", header: "Quote" },
    { key: "party", header: "Customer", render: (r) => r.client_name || r.lead_name || "—" },
    { key: "total", header: "Total", render: (r) => formatMoney(r.total, r.currency) },
    { key: "valid_until", header: "Valid until", render: (r) => formatDate(r.valid_until) },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "revision", header: "Rev." },
    { key: "created_by_name", header: "Created by" },
  ];

  return (
    <>
      <PageHeader title="Quotations" subtitle="Prepare quotes and get them approved"
                  actions={canWrite && <Link className="btn btn-primary" to="/sales/quotations/new">New quotation</Link>} />
      {canWrite && <ApprovalPanel />}
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search quote number or customer…" />
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
                 onRowClick={(r) => navigate(`/sales/quotations/${r.id}`)}
                 emptyTitle="No quotations found" emptyHint="Create a quotation for a client or a lead."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
    </>
  );
}