import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatDateTime, formatMoney, nowLocalInput, titleCase, toIso } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import { SelectField, TextAreaField, TextField } from "../../components/forms/fields";
import LeadFormModal from "./LeadFormModal";
import { ConvertDialog, QualifyDialog } from "./LeadDialogs";

const KINDS = ["call", "email", "meeting", "note", "follow_up"].map((v) => ({ value: v, label: titleCase(v) }));

function ActivityCard({ leadId, locked }) {
  const qc = useQueryClient();
  const activities = useDetail("/leads/", leadId, "activities/");
  const blank = () => ({ kind: "call", description: "", activity_date: nowLocalInput(), next_follow_up: "" });
  const form = useFormState(blank());
  const add = useApiAction(
    async (body) => unwrap(await api.post(`/leads/${leadId}/activities/`, body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/leads/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const r = await add.run({ kind: v.kind, description: v.description, activity_date: toIso(v.activity_date),
                              next_follow_up: toIso(v.next_follow_up) });
    if (r.ok) form.reset(blank()); else form.setErrors(r.error.fields);
  }
  const rows = [...(activities.data ?? [])].sort((a, b) => b.activity_date.localeCompare(a.activity_date));

  return (
    <section className="card">
      <h3>Activities</h3>
      {!locked && (
        <form onSubmit={submit} className="inline-form">
          <ErrorBanner message={add.error?.message} />
          <SelectField form={form} name="kind" label="Type" options={KINDS} required />
          <TextAreaField form={form} name="description" label="What happened?" rows={2} required />
          <TextField form={form} name="activity_date" label="When" type="datetime-local" required />
          <TextField form={form} name="next_follow_up" label="Next follow-up" type="datetime-local" />
          <button className="btn btn-primary" disabled={add.busy}>{add.busy ? "Saving…" : "Add activity"}</button>
        </form>
      )}
      {activities.isLoading ? <Spinner /> : rows.length === 0 ? <EmptyState title="No activities yet" /> : (
        <ul className="activity">
          {rows.map((a) => (
            <li key={a.id}>
              <strong>{titleCase(a.kind)}</strong> {a.description}
              <small className="muted">
                {formatDateTime(a.activity_date)} · {a.created_by_name}
                {a.next_follow_up && ` · follow up ${formatDateTime(a.next_follow_up)}`}
              </small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function LeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const lead = useDetail("/leads/", id);
  const history = useDetail("/leads/", id, "history/");
  const [dialog, setDialog] = useState(null);       // "edit" | "qualify" | "unqualify" | "convert"
  const refresh = () => qc.invalidateQueries({ queryKey: ["/leads/"] });
  const follow = useApiAction(async (status) => unwrap(await api.post(`/leads/${id}/status/`, { status })), { onSuccess: refresh });
  const unqualify = useApiAction(async (reason) => unwrap(await api.post(`/leads/${id}/unqualify/`, { reason })), { onSuccess: refresh });

  if (lead.isLoading) return <Spinner />;
  if (lead.error) return <ErrorBanner message={parseApiError(lead.error).message} onRetry={lead.refetch} />;
  const l = lead.data;
  const s = l.status;
  const converted = s === "converted";

  return (
    <>
      <PageHeader
        title={<>{l.name} <StatusBadge status={s} /></>}
        subtitle={l.company_name || "No company"}
        actions={
          <>
            <Link className="btn btn-ghost" to="/crm/leads">Back</Link>
            {!converted && <button className="btn btn-ghost" onClick={() => setDialog("edit")}>Edit</button>}
            {["new", "contacted", "pending", "unqualified"].includes(s) && s !== "contacted" &&
              <button className="btn btn-ghost" disabled={follow.busy} onClick={() => follow.run("contacted")}>Mark contacted</button>}
            {["new", "contacted", "unqualified"].includes(s) &&
              <button className="btn btn-ghost" disabled={follow.busy} onClick={() => follow.run("pending")}>Mark pending</button>}
            {["new", "contacted", "pending"].includes(s) &&
              <button className="btn btn-primary" onClick={() => setDialog("qualify")}>Qualify</button>}
            {["new", "contacted", "pending", "qualified"].includes(s) &&
              <button className="btn btn-danger" onClick={() => setDialog("unqualify")}>Mark unqualified</button>}
            {s === "qualified" && <button className="btn btn-primary" onClick={() => setDialog("convert")}>Convert to client</button>}
          </>
        }
      />
      <ErrorBanner message={follow.error?.message} />
      {converted && l.converted_client && (
        <div className="banner success">This lead was converted. <Link to={`/crm/clients/${l.converted_client}`}>Open the client</Link></div>
      )}
      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Email", l.email], ["Phone", l.phone || null], ["Source", l.source || null],
            ["Branch", l.branch_name], ["Salesperson", l.owner_name], ["Created", formatDate(l.created_at)], ["Notes", l.notes || null]]} />
        </section>
        <section className="card">
          <h3>Qualification</h3>
          <InfoGrid items={[["Business requirement", l.business_requirement || null],
            ["Budget", l.budget ? formatMoney(l.budget) : null], ["Customer interest", l.customer_interest || null],
            ["Expected timeline", l.expected_timeline || null],
            ...(s === "unqualified" ? [["Reason", l.unqualified_reason]] : [])]} />
        </section>
        <ActivityCard leadId={id} locked={converted} />
        <section className="card">
          <h3>Status history</h3>
          {history.data?.length ? (
            <ul className="activity">
              {history.data.map((h, i) => (
                <li key={i}>
                  <StatusBadge status={h.from_status} /> → <StatusBadge status={h.to_status} />
                  {h.reason && <em> {h.reason}</em>}
                  <small className="muted">{formatDateTime(h.created_at)}</small>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No status changes yet" />}
        </section>
      </div>

      {dialog === "edit" && <LeadFormModal lead={l} onClose={() => setDialog(null)} onSaved={() => setDialog(null)} />}
      {dialog === "qualify" && <QualifyDialog lead={l} onClose={() => setDialog(null)} />}
      {dialog === "convert" && <ConvertDialog lead={l} onClose={() => setDialog(null)}
                                              onConverted={(client) => navigate(`/crm/clients/${client.id}`)} />}
      <ConfirmDialog open={dialog === "unqualify"} title="Mark lead as unqualified" danger requireReason
                     message="Explain why this lead is not a fit. The reason is kept in the lead's history."
                     confirmLabel="Mark unqualified" busy={unqualify.busy} error={unqualify.error?.message}
                     onCancel={() => setDialog(null)}
                     onConfirm={async (reason) => { const r = await unqualify.run(reason); if (r.ok) setDialog(null); }} />
    </>
  );
}