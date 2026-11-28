import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatMoney, titleCase } from "../../utils/format";
import { PAYMENT_ACTIONS } from "../../utils/workflow";
import PageHeader from "../../components/common/PageHeader";
import ErrorBanner from "../../components/common/ErrorBanner";
import StatusBadge from "../../components/common/StatusBadge";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";

const STATUSES = ["pending", "confirmed", "reconciled", "rejected"].map((v) => ({ value: v, label: titleCase(v) }));
const METHODS = ["bank_transfer", "cash", "mobile_money", "card", "cheque"].map((v) => ({ value: v, label: titleCase(v) }));

function ReconciliationTiles({ filters }) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v != null));
  const q = useQuery({
    queryKey: ["/payments/", "summary", params],
    queryFn: async () => unwrap(await api.get("/payments/summary/", { params })),
  });
  const rows = q.data ?? [];
  return (
    <div className="stage-tiles">
      {STATUSES.map((s) => {
        const mine = rows.filter((r) => r.status === s.value);
        return (
          <div key={s.value} className="kpi">
            <span className="muted">{s.label}</span>
            <strong>{mine.reduce((a, r) => a + r.count, 0)}</strong>
            <small className="muted">{mine.map((r) => formatMoney(r.total, r.invoice__currency)).join(" · ") || "—"}</small>
          </div>
        );
      })}
    </div>
  );
}

export default function PaymentsPage() {
  const qc = useQueryClient();
  const list = usePaginatedList("/payments/");
  const [rejecting, setRejecting] = useState(null);
  const act = useApiAction(
    async ({ id, verb, body }) => unwrap(await api.post(`/payments/${id}/${verb}/`, body)),
    { onSuccess: () => { qc.invalidateQueries({ queryKey: ["/payments/"] }); qc.invalidateQueries({ queryKey: ["/invoices/"] }); } }
  );
  const run = (id, verb, body) => { act.reset(); return act.run({ id, verb, body }); };

  const columns = [
    { key: "payment_number", header: "Payment" },
    { key: "invoice_number", header: "Invoice" },
    { key: "client_name", header: "Client" },
    { key: "amount", header: "Amount", render: (r) => formatMoney(r.amount, r.currency) },
    { key: "method", header: "Method", render: (r) => titleCase(r.method) },
    { key: "reference", header: "Reference" },
    { key: "payment_date", header: "Date", render: (r) => formatDate(r.payment_date) },
    { key: "status", header: "Status", render: (r) => (
      <div className="stack"><StatusBadge status={r.status} />{r.reject_reason && <small className="error-text">{r.reject_reason}</small>}</div>
    ) },
    { key: "actions", header: "", render: (r) => (
      <div className="page-actions">
        {PAYMENT_ACTIONS[r.status].map((verb) => verb === "reject"
          ? <button key={verb} className="btn btn-danger" onClick={() => { act.reset(); setRejecting(r); }}>Reject</button>
          : <button key={verb} className="btn btn-primary" disabled={act.busy} onClick={() => run(r.id, verb)}>{titleCase(verb)}</button>)}
      </div>
    ) },
  ];

  return (
    <>
      <PageHeader title="Payments" subtitle="Simulated payments and their reconciliation" />
      <ReconciliationTiles filters={list.filters} />
      <ErrorBanner message={act.error?.message} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search payment, reference, invoice, client…" />
        <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                      onChange={(v) => list.setFilter("status", v)} options={STATUSES} />
        <FilterSelect label="Method" allLabel="All methods" value={list.filters.method ?? ""}
                      onChange={(v) => list.setFilter("method", v)} options={METHODS} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 emptyTitle="No payments found" emptyHint="Record a payment from an issued invoice."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      <ConfirmDialog open={Boolean(rejecting)} title="Reject payment" danger requireReason confirmLabel="Reject payment"
                     message="The invoice balance is recalculated without this payment."
                     busy={act.busy} error={act.error?.message} onCancel={() => setRejecting(null)}
                     onConfirm={async (reason) => { const r = await run(rejecting.id, "reject", { reason }); if (r.ok) setRejecting(null); }} />
    </>
  );
}
