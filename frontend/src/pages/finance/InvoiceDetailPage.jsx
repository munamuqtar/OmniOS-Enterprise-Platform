import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import RecordPaymentDialog from "./RecordPaymentDialog";

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const invoice = useDetail("/invoices/", id);
  const payments = useDetail("/invoices/", id, "payments/");
  const history = useDetail("/invoices/", id, "history/");
  const [dialog, setDialog] = useState(null);           // "issue" | "cancel" | "pay"
  const refresh = () => qc.invalidateQueries({ queryKey: ["/invoices/"] });
  const issue = useApiAction(async () => unwrap(await api.post(`/invoices/${id}/issue/`)), { onSuccess: refresh });
  const cancel = useApiAction(async (reason) => unwrap(await api.post(`/invoices/${id}/cancel/`, { reason })), { onSuccess: refresh });

  if (invoice.isLoading) return <Spinner />;
  if (invoice.error) return <ErrorBanner message={parseApiError(invoice.error).message} onRetry={invoice.refetch} />;
  const inv = invoice.data;
  const canWrite = hasRole("finance");
  const open = ["issued", "partially_paid", "overdue"].includes(inv.status);
  const money = (v) => formatMoney(v, inv.currency);

  return (
    <>
      <PageHeader title={<>{inv.invoice_number} <StatusBadge status={inv.status} /></>}
        subtitle={<>{inv.client_name} · <Link to={`/projects/${inv.project}`}>{inv.project_code}</Link></>}
        actions={
          <>
            <Link className="btn btn-ghost" to="/finance/invoices">Back</Link>
            {canWrite && inv.status === "draft" && <button className="btn btn-primary" onClick={() => setDialog("issue")}>Issue invoice</button>}
            {canWrite && open && <button className="btn btn-primary" onClick={() => setDialog("pay")}>Record payment</button>}
            {canWrite && (inv.status === "draft" || open) &&
              <button className="btn btn-danger" onClick={() => setDialog("cancel")}>Cancel invoice</button>}
          </>
        } />
      <ErrorBanner message={issue.error?.message} />
      {inv.status === "cancelled" && <div className="banner error">Cancelled: {inv.cancel_reason}</div>}
      {inv.status === "overdue" && <div className="banner error">This invoice is past its due date ({formatDate(inv.due_date)}).</div>}

      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Client", inv.client_name], ["Issued", formatDate(inv.issue_date)], ["Due", formatDate(inv.due_date)],
            ["Currency", inv.currency], ["Notes", inv.notes || null]]} />
        </section>
        <section className="card">
          <h3>Totals</h3>
          <InfoGrid items={[["Subtotal", money(inv.subtotal)], ["Discount", money(inv.discount)],
            [`Tax (${formatNumber(inv.tax_rate)}%)`, money(inv.tax)], ["Total", <strong key="t">{money(inv.total)}</strong>],
            ["Paid", money(inv.amount_paid)], ["Balance", <strong key="b">{money(inv.balance)}</strong>]]} />
        </section>
      </div>

      <section className="card panel-gap">
        <h3>Billed work</h3>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Description</th><th>Hours</th><th>Rate</th><th>Line total</th></tr></thead>
            <tbody>
              {inv.items.map((i) => (
                <tr key={i.id}><td>{i.description}</td><td>{formatNumber(i.quantity)}</td><td>{money(i.unit_price)}</td><td>{money(i.line_total)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="section-grid panel-gap">
        <section className="card">
          <h3>Payments</h3>
          {payments.data?.length ? (
            <ul className="activity">
              {payments.data.map((p) => (
                <li key={p.id}>
                  <strong>{p.payment_number}</strong> <StatusBadge status={p.status} /> {formatMoney(p.amount, p.currency)}
                  <small className="muted">{formatDate(p.payment_date)} · {p.method.replace("_", " ")} · ref {p.reference}</small>
                  {p.reject_reason && <small className="error-text">Rejected: {p.reject_reason}</small>}
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No payments yet" />}
        </section>
        <section className="card">
          <h3>Status history</h3>
          {history.data?.length ? (
            <ul className="activity">
              {history.data.map((h, i) => (
                <li key={i}>
                  {h.from_status && <><StatusBadge status={h.from_status} /> → </>}<StatusBadge status={h.to_status} />
                  {h.reason && <em> {h.reason}</em>}
                  <small className="muted">{formatDateTime(h.created_at)}</small>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No history" />}
        </section>
      </div>

      <ConfirmDialog open={dialog === "issue"} title="Issue invoice" confirmLabel="Issue invoice" busy={issue.busy}
                     message="Issuing locks the items and totals and makes the invoice payable. Drafts can no longer be edited afterwards."
                     onCancel={() => setDialog(null)}
                     onConfirm={async () => { const r = await issue.run(); if (r.ok) setDialog(null); }} />
      <ConfirmDialog open={dialog === "cancel"} title="Cancel invoice" danger requireReason confirmLabel="Cancel invoice" busy={cancel.busy}
                     message="The billed timesheets become available for invoicing again. An invoice with payments must have those payments rejected first."
                     error={cancel.error?.message} onCancel={() => setDialog(null)}
                     onConfirm={async (reason) => { const r = await cancel.run(reason); if (r.ok) setDialog(null); }} />
      {dialog === "pay" && <RecordPaymentDialog invoice={inv} onClose={() => setDialog(null)} />}
    </>
  );
}
