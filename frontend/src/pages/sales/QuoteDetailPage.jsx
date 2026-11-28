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
import ConvertQuoteDialog from "./ConvertQuoteDialog";

export default function QuoteDetailPage() {
  const { id } = useParams();
  const { user, hasRole } = useAuth();
  const qc = useQueryClient();
  const quote = useDetail("/quotes/", id);
  const approvals = useDetail("/quotes/", id, "approvals/");
  const [dialog, setDialog] = useState(null);          // "reject" | "convert"
  const [notice, setNotice] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["/quotes/"] });
  const post = (path, body) => async () => unwrap(await api.post(`/quotes/${id}/${path}/`, body));
  const submitQ = useApiAction(post("submit"), { onSuccess: refresh });
  const approveQ = useApiAction(post("approve"), { onSuccess: refresh });
  const reviseQ = useApiAction(post("revise"), { onSuccess: refresh });
  const rejectQ = useApiAction(async (reason) => unwrap(await api.post(`/quotes/${id}/reject/`, { reason })), { onSuccess: refresh });

  if (quote.isLoading) return <Spinner />;
  if (quote.error) return <ErrorBanner message={parseApiError(quote.error).message} onRetry={quote.refetch} />;
  const q = quote.data;
  const canWrite = hasRole("sales");
  const mine = q.created_by === user.id;
  const lastRejection = [...(approvals.data ?? [])].reverse().find((a) => a.decision === "rejected");
  const actionError = submitQ.error || approveQ.error || reviseQ.error;

  return (
    <>
      <PageHeader title={<>{q.quote_number} <StatusBadge status={q.status} /></>}
        subtitle={`Revision ${q.revision} · ${q.client_name || q.lead_name}`}
        actions={
          <>
            <Link className="btn btn-ghost" to="/sales/quotations">Back</Link>
            {canWrite && ["draft", "rejected"].includes(q.status) && (
              <>
                <Link className="btn btn-ghost" to={`/sales/quotations/${id}/edit`}>Edit</Link>
                <button className="btn btn-primary" disabled={submitQ.busy} onClick={() => submitQ.run()}>Submit for approval</button>
              </>
            )}
            {canWrite && q.status === "pending_approval" && !mine && (
              <>
                <button className="btn btn-primary" disabled={approveQ.busy} onClick={() => approveQ.run()}>Approve</button>
                <button className="btn btn-danger" onClick={() => setDialog("reject")}>Reject</button>
              </>
            )}
            {canWrite && q.status === "approved" && (
              <>
                <button className="btn btn-ghost" disabled={reviseQ.busy} onClick={() => reviseQ.run()}>Reopen for revision</button>
                {!q.converted_project && <button className="btn btn-primary" onClick={() => setDialog("convert")}>Convert to project</button>}
              </>
            )}
          </>
        } />
      <ErrorBanner message={actionError?.message} />
      {notice && <div className="banner success">{notice}</div>}
      {q.status === "pending_approval" && mine && <div className="banner info">Waiting for a manager to approve this quotation. You cannot approve your own quote.</div>}
      {q.status === "rejected" && lastRejection && <div className="banner error">Rejected: {lastRejection.reason}</div>}
      {q.converted_project && !notice && <div className="banner success">This quotation has been converted to a project.</div>}

      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Customer", q.client_name || q.lead_name], ["Valid until", formatDate(q.valid_until)],
            ["Currency", q.currency], ["Payment terms", q.payment_terms || null], ["Created by", q.created_by_name],
            ["Notes", q.notes || null]]} />
        </section>
        <section className="card">
          <h3>Totals</h3>
          <InfoGrid items={[["Subtotal", formatMoney(q.subtotal, q.currency)], ["Discount", formatMoney(q.discount, q.currency)],
            [`Tax (${formatNumber(q.tax_rate)}%)`, formatMoney(q.tax, q.currency)], ["Total", <strong key="t">{formatMoney(q.total, q.currency)}</strong>]]} />
        </section>
      </div>

      <section className="card panel-gap">
        <h3>Items</h3>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Description</th><th>Quantity</th><th>Unit price</th><th>Line total</th></tr></thead>
            <tbody>
              {q.items.map((i) => (
                <tr key={i.id}><td>{i.description}</td><td>{formatNumber(i.quantity)}</td>
                  <td>{formatMoney(i.unit_price, q.currency)}</td><td>{formatMoney(i.line_total, q.currency)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card panel-gap">
        <h3>Approval history</h3>
        {approvals.data?.length ? (
          <ul className="activity">
            {approvals.data.map((a, i) => (
              <li key={i}>
                <StatusBadge status={a.decision} /> by <strong>{a.actor_name}</strong> (revision {a.revision})
                {a.reason && <em> {a.reason}</em>}
                <small className="muted">{formatDateTime(a.created_at)}</small>
              </li>
            ))}
          </ul>
        ) : <EmptyState title="Not submitted yet" />}
      </section>

      <ConfirmDialog open={dialog === "reject"} title="Reject quotation" danger requireReason confirmLabel="Reject"
                     message="Tell the salesperson what to fix. They can correct the quotation and submit it again."
                     busy={rejectQ.busy} error={rejectQ.error?.message} onCancel={() => setDialog(null)}
                     onConfirm={async (reason) => { const r = await rejectQ.run(reason); if (r.ok) setDialog(null); }} />
      {dialog === "convert" && (
        <ConvertQuoteDialog quote={q} onClose={() => setDialog(null)}
                            onConverted={(p) => { setDialog(null); setNotice(`Project ${p.project_code} was created. It is in Draft until the project manager plans it.`); }} />
      )}
    </>
  );
}