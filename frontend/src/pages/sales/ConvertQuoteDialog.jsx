import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { todayIso } from "../../utils/format";
import Modal from "../../components/modals/Modal";
import ErrorBanner from "../../components/common/ErrorBanner";
import { LookupField, TextAreaField, TextField } from "../../components/forms/fields";

export default function ConvertQuoteDialog({ quote, onClose, onConverted }) {
  const qc = useQueryClient();
  const form = useFormState({
    name: `${quote.client_name || quote.lead_name || "Project"} – ${quote.quote_number}`,
    manager: "", start_date: todayIso(), end_date: todayIso(90), description: "",
  });
  const action = useApiAction(async (body) => unwrap(await api.post(`/quotes/${quote.id}/convert/`, body)), {
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["/quotes/"] }); qc.invalidateQueries({ queryKey: ["/projects/"] }); },
  });
  async function submit(e) {
    e.preventDefault();
    const r = await action.run(form.values);
    if (r.ok) onConverted(r.data.project); else form.setErrors(r.error.fields);
  }
  return (
    <Modal title="Convert to project" onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="convert-quote-form" disabled={action.busy}>{action.busy ? "Creating…" : "Create project"}</button>
      </>
    }>
      <form id="convert-quote-form" onSubmit={submit}>
        <ErrorBanner message={action.error?.message} />
        <p className="muted">Creates a draft project for this client, with the quote total as its budget.</p>
        <TextField form={form} name="name" label="Project name" required />
        <LookupField form={form} name="manager" label="Project manager" endpoint="/lookups/users/"
                     params={{ role: "project_manager" }} labelOf={(u) => u.name} required />
        <TextField form={form} name="start_date" label="Start date" type="date" required />
        <TextField form={form} name="end_date" label="End date" type="date" required />
        <TextAreaField form={form} name="description" label="Description" />
      </form>
    </Modal>
  );
}