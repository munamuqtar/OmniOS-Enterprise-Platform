import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useDetail } from "../../hooks/useDetail";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatDateTime, formatMoney } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import ClientFormModal from "./ClientFormModal";

function ClientQuotes({ clientId }) {
  const q = useQuery({
    queryKey: ["/quotes/", "client", clientId],
    queryFn: async () => unwrap(await api.get("/quotes/", { params: { client: clientId } })).results,
  });
  return (
    <section className="card">
      <h3>Quotations</h3>
      {q.isLoading ? <Spinner /> : q.data?.length ? (
        <ul className="activity">
          {q.data.map((x) => (
            <li key={x.id}>
              <Link to={`/sales/quotations/${x.id}`}>{x.quote_number}</Link> <StatusBadge status={x.status} /> {formatMoney(x.total, x.currency)}
              <small className="muted">Valid until {formatDate(x.valid_until)}</small>
            </li>
          ))}
        </ul>
      ) : <EmptyState title="No quotations yet" />}
    </section>
  );
}

export default function ClientDetailPage() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const client = useDetail("/clients/", id);
  const history = useDetail("/clients/", id, "history/");
  const [editing, setEditing] = useState(false);

  if (client.isLoading) return <Spinner />;
  if (client.error) return <ErrorBanner message={parseApiError(client.error).message} onRetry={client.refetch} />;
  const c = client.data;
  const canWrite = hasRole("sales");

  return (
    <>
      <PageHeader title={<>{c.name} <StatusBadge status={c.status} /></>} subtitle={c.company_name || "No company"}
        actions={
          <>
            <Link className="btn btn-ghost" to="/crm/clients">Back</Link>
            {canWrite && <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>}
            {canWrite && <Link className="btn btn-primary" to={`/sales/quotations/new?client=${c.id}&name=${encodeURIComponent(c.name)}`}>New quotation</Link>}
          </>
        } />
      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Contact", c.contact_person || null], ["Email", c.email], ["Phone", c.phone || null],
            ["Address", c.address || null], ["Branch", c.branch_name], ["Created", formatDate(c.created_at)]]} />
        </section>
        {hasRole("sales", "finance") && <ClientQuotes clientId={id} />}
        <section className="card">
          <h3>History</h3>
          {history.data?.source_lead ? (
            <>
              <p className="muted">Converted from a lead.</p>
              <ul className="activity">
                {history.data.lead_history.map((h, i) => (
                  <li key={i}>
                    <StatusBadge status={h.from_status} /> → <StatusBadge status={h.to_status} />
                    <small className="muted">{formatDateTime(h.created_at)}</small>
                  </li>
                ))}
              </ul>
            </>
          ) : <EmptyState title="Created directly" hint="This client was not converted from a lead." />}
        </section>
      </div>
      {editing && <ClientFormModal client={c} onClose={() => setEditing(false)} onSaved={() => setEditing(false)} />}
    </>
  );
}