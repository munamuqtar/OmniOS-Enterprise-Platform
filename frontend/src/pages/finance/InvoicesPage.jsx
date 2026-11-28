import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatKpi, formatMoney, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";

const STATUSES = ["draft", "issued", "partially_paid", "paid", "overdue", "cancelled"].map((v) => ({ value: v, label: titleCase(v) }));
const OPEN = ["issued", "partially_paid", "overdue"];

function InvoiceTiles({ filters }) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v != null));
  const q = useQuery({
    queryKey: ["/invoices/", "summary", params],
    queryFn: async () => unwrap(await api.get("/invoices/summary/", { params })),
  });
  const rows = q.data ?? [];
  const outstanding = {};
  rows.filter((r) => OPEN.includes(r.status)).forEach((r) => { outstanding[r.currency] = (outstanding[r.currency] ?? 0) + Number(r.balance ?? 0); });
  const count = (s) => rows.filter((r) => r.status === s).reduce((a, r) => a + r.count, 0);
  return (
    <div className="stage-tiles">
      <div className="kpi"><span className="muted">Outstanding</span><strong>{formatKpi(Object.entries(outstanding).map(([currency, amount]) => ({ currency, amount })))}</strong></div>
      <div className="kpi"><span className="muted">Overdue</span><strong>{count("overdue")}</strong></div>
      <div className="kpi"><span className="muted">Paid</span><strong>{count("paid")}</strong></div>
      <div className="kpi"><span className="muted">Drafts</span><strong>{count("draft")}</strong></div>
    </div>
  );
}

export default function InvoicesPage() {
  const { hasRole } = useAuth();
  const list = usePaginatedList("/invoices/");
  const branches = useBranchOptions();
  const navigate = useNavigate();

  const columns = [
    { key: "invoice_number", header: "Invoice" },
    { key: "client_name", header: "Client" },
    { key: "project_code", header: "Project" },
    { key: "total", header: "Total", render: (r) => formatMoney(r.total, r.currency) },
    { key: "balance", header: "Balance", render: (r) => formatMoney(r.balance, r.currency) },
    { key: "due_date", header: "Due", render: (r) => formatDate(r.due_date) },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
  ];

  return (
    <>
      <PageHeader title="Invoices" subtitle="Bill approved project work"
                  actions={hasRole("finance") && <Link className="btn btn-primary" to="/finance/invoices/new">New invoice</Link>} />
      <InvoiceTiles filters={list.filters} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search number, client, project…" />
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
                 onRowClick={(r) => navigate(`/finance/invoices/${r.id}`)}
                 emptyTitle="No invoices found" emptyHint="Invoices are built from approved timesheets."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
    </>
  );
}
