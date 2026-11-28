import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { parseApiError } from "../../utils/errors";
import { formatDateTime } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import FormDialog from "../../components/modals/FormDialog";
import { SelectField } from "../../components/forms/fields";
import CandidateFormModal from "./CandidateFormModal";

function ApplyDialog({ candidate, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({ vacancy: "" });
  const vacancies = useQuery({
    queryKey: ["/vacancies/", "open", candidate.branch],
    queryFn: async () => unwrap(await api.get("/vacancies/", { params: { status: "open", branch: candidate.branch } })).results,
  });
  const save = useApiAction(async (body) => unwrap(await api.post("/recruitment-applications/", body)),
                            { onSuccess: () => qc.invalidateQueries({ queryKey: ["/recruitment-applications/"] }) });
  async function submit(e) {
    e.preventDefault();
    const r = await save.run({ candidate: candidate.id, vacancy: form.values.vacancy });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title="Apply to a vacancy" formId="apply-form" busy={save.busy} error={save.error?.message}
                onClose={onClose} submitLabel="Create application">
      <form id="apply-form" onSubmit={submit}>
        <SelectField form={form} name="vacancy" label="Open vacancy" required
                     hint="Only open vacancies in the candidate's branch are listed."
                     options={(vacancies.data ?? []).map((v) => ({ value: v.id, label: v.title }))} />
        {form.errors.non_field_errors && <p className="error-text">{form.errors.non_field_errors}</p>}
      </form>
    </FormDialog>
  );
}

export default function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const candidate = useDetail("/candidates/", id);
  const apps = useQuery({
    queryKey: ["/recruitment-applications/", "candidate", id],
    queryFn: async () => unwrap(await api.get("/recruitment-applications/", { params: { candidate: id } })).results,
  });
  const [dialog, setDialog] = useState(null);            // "edit" | "apply"

  if (candidate.isLoading) return <Spinner />;
  if (candidate.error) return <ErrorBanner message={parseApiError(candidate.error).message} onRetry={candidate.refetch} />;
  const c = candidate.data;

  return (
    <>
      <PageHeader title={`${c.first_name} ${c.last_name}`} subtitle={c.email}
                  actions={
                    <>
                      <Link className="btn btn-ghost" to="/hr/recruitment">Back</Link>
                      <button className="btn btn-ghost" onClick={() => setDialog("edit")}>Edit</button>
                      <button className="btn btn-primary" onClick={() => setDialog("apply")}>Apply to vacancy</button>
                    </>
                  } />
      <div className="section-grid">
        <section className="card">
          <h3>Profile</h3>
          <InfoGrid items={[["Phone", c.phone || null], ["Branch", c.branch_name], ["Source", c.source || null],
            ["Summary", c.summary || null],
            ["Resume", c.resume ? <a key="r" href={c.resume} target="_blank" rel="noreferrer">Open resume</a> : null]]} />
        </section>
        <section className="card">
          <h3>Applications</h3>
          {apps.data?.length ? (
            <ul className="activity">
              {apps.data.map((a) => (
                <li key={a.id}>
                  <Link to={`/hr/recruitment/applications/${a.id}`}>{a.vacancy_title}</Link> <StatusBadge status={a.stage} />
                  <small className="muted">Applied {formatDateTime(a.created_at)}</small>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No applications yet" />}
        </section>
      </div>
      {dialog === "edit" && <CandidateFormModal candidate={c} onClose={() => setDialog(null)} onSaved={() => setDialog(null)} />}
      {dialog === "apply" && <ApplyDialog candidate={c} onClose={() => { setDialog(null); navigate(0); }} />}
    </>
  );
}