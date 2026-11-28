import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { parseApiError } from "../../utils/errors";
import { formatDateTime, titleCase, toIso } from "../../utils/format";
import { RECRUIT_NEXT } from "../../utils/workflow";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import ConfirmDialog from "../../components/modals/ConfirmDialog";
import FormDialog from "../../components/modals/FormDialog";
import { TextAreaField, TextField } from "../../components/forms/fields";

function InterviewDialog({ busy, error, onClose, onSubmit }) {
  const form = useFormState({ interview_at: "", interview_location: "" });
  return (
    <FormDialog title="Schedule the interview" formId="interview-form" busy={busy} error={error} onClose={onClose} submitLabel="Move to interview">
      <form id="interview-form" onSubmit={(e) => { e.preventDefault(); onSubmit(form.values); }}>
        <TextField form={form} name="interview_at" label="Date and time" type="datetime-local" required />
        <TextField form={form} name="interview_location" label="Location or link" />
      </form>
    </FormDialog>
  );
}

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const app = useDetail("/recruitment-applications/", id);
  const notes = useDetail("/recruitment-applications/", id, "notes/");
  const history = useDetail("/recruitment-applications/", id, "history/");
  const [target, setTarget] = useState(null);            // the stage we are about to move to
  const noteForm = useFormState({ note: "" });
  const refresh = () => qc.invalidateQueries({ queryKey: ["/recruitment-applications/"] });
  const move = useApiAction(async (body) => unwrap(await api.post(`/recruitment-applications/${id}/stage/`, body)), { onSuccess: refresh });
  const addNote = useApiAction(async (body) => unwrap(await api.post(`/recruitment-applications/${id}/notes/`, body)), { onSuccess: refresh });

  if (app.isLoading) return <Spinner />;
  if (app.error) return <ErrorBanner message={parseApiError(app.error).message} onRetry={app.refetch} />;
  const a = app.data;
  const sortedNotes = [...(notes.data ?? [])].sort((x, y) => y.created_at.localeCompare(x.created_at));

  async function submitNote(e) {
    e.preventDefault();
    const r = await addNote.run({ note: noteForm.values.note });
    if (r.ok) noteForm.reset(); else noteForm.setErrors(r.error.fields);
  }

  return (
    <>
      <PageHeader title={<>{a.candidate_name} <StatusBadge status={a.stage} /></>} subtitle={a.vacancy_title}
        actions={
          <>
            <Link className="btn btn-ghost" to="/hr/recruitment">Back</Link>
            <Link className="btn btn-ghost" to={`/hr/recruitment/candidates/${a.candidate}`}>Candidate profile</Link>
            {RECRUIT_NEXT[a.stage].map((s) => (
              <button key={s} className={`btn ${s === "rejected" ? "btn-danger" : "btn-primary"}`}
                      onClick={() => { move.reset(); setTarget(s); }}>
                {s === "rejected" ? "Reject" : `Move to ${titleCase(s)}`}
              </button>
            ))}
          </>
        } />
      {a.stage === "rejected" && <div className="banner error">Rejected: {a.rejection_reason}</div>}
      {a.stage === "hired" && <div className="banner success">This candidate was hired. You can now create their employee record.</div>}

      <div className="section-grid">
        <section className="card">
          <h3>Details</h3>
          <InfoGrid items={[["Vacancy", a.vacancy_title], ["Applied", formatDateTime(a.created_at)],
            ["Interview", a.interview_at ? formatDateTime(a.interview_at) : null], ["Location", a.interview_location || null]]} />
        </section>
        <section className="card">
          <h3>Stage history</h3>
          {history.data?.length ? (
            <ul className="activity">
              {history.data.map((h, i) => (
                <li key={i}>
                  <StatusBadge status={h.from_stage} /> → <StatusBadge status={h.to_stage} />
                  {h.reason && <em> {h.reason}</em>}
                  <small className="muted">{formatDateTime(h.created_at)}</small>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No stage changes yet" />}
        </section>
        <section className="card">
          <h3>Notes</h3>
          <form onSubmit={submitNote} className="inline-form">
            <ErrorBanner message={addNote.error?.message} />
            <TextAreaField form={noteForm} name="note" label="Add a note" rows={2} required />
            <button className="btn btn-primary" disabled={addNote.busy}>Add note</button>
          </form>
          {sortedNotes.length ? (
            <ul className="activity">
              {sortedNotes.map((n) => (
                <li key={n.id}>{n.note}<small className="muted">{n.author_name} · {formatDateTime(n.created_at)}</small></li>
              ))}
            </ul>
          ) : <EmptyState title="No notes yet" />}
        </section>
      </div>

      {target === "interview" && (
        <InterviewDialog busy={move.busy} error={move.error?.message} onClose={() => setTarget(null)}
          onSubmit={async (v) => {
            const r = await move.run({ stage: "interview", interview_at: toIso(v.interview_at), interview_location: v.interview_location });
            if (r.ok) setTarget(null);
          }} />
      )}
      <ConfirmDialog open={Boolean(target) && target !== "interview"} danger={target === "rejected"} requireReason={target === "rejected"}
                     title={target === "rejected" ? "Reject application" : "Move application"}
                     confirmLabel={target === "rejected" ? "Reject" : `Move to ${titleCase(target ?? "")}`}
                     message={target === "rejected" ? "Record why this candidate is not moving forward." : `Move this application to ${titleCase(target ?? "")}?`}
                     busy={move.busy} error={move.error?.message} onCancel={() => setTarget(null)}
                     onConfirm={async (reason) => { const r = await move.run({ stage: target, reason }); if (r.ok) setTarget(null); }} />
    </>
  );
}