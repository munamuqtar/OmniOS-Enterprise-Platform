import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import Modal from "../../components/modals/Modal";
import ErrorBanner from "../../components/common/ErrorBanner";
import { TextAreaField, TextField } from "../../components/forms/fields";

function FormDialog({ title, formId, action, onClose, submitLabel, children }) {
  return (
    <Modal title={title} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form={formId} disabled={action.busy}>{action.busy ? "Working…" : submitLabel}</button>
      </>
    }>
      <ErrorBanner message={action.error?.message} />
      {children}
    </Modal>
  );
}

export function QualifyDialog({ lead, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({
    business_requirement: lead.business_requirement ?? "", budget: lead.budget ?? "",
    customer_interest: lead.customer_interest ?? "", expected_timeline: lead.expected_timeline ?? "", notes: lead.notes ?? "",
  });
  const action = useApiAction(async (body) => unwrap(await api.post(`/leads/${lead.id}/qualify/`, body)),
                              { onSuccess: () => qc.invalidateQueries({ queryKey: ["/leads/"] }) });
  async function submit(e) {
    e.preventDefault();
    const r = await action.run(form.values);
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title="Qualify lead" formId="qualify-form" action={action} onClose={onClose} submitLabel="Mark as qualified">
      <form id="qualify-form" onSubmit={submit}>
        <TextAreaField form={form} name="business_requirement" label="Business requirement" required />
        <TextField form={form} name="budget" label="Budget" type="number" min="0" step="0.01" required />
        <TextField form={form} name="customer_interest" label="Customer interest" required />
        <TextField form={form} name="expected_timeline" label="Expected timeline" required />
        <TextAreaField form={form} name="notes" label="Notes" />
      </form>
    </FormDialog>
  );
}

export function ConvertDialog({ lead, onClose, onConverted }) {
  const qc = useQueryClient();
  const form = useFormState({ address: "", contact_person: lead.name });
  const action = useApiAction(async (body) => unwrap(await api.post(`/leads/${lead.id}/convert/`, body)), {
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["/leads/"] }); qc.invalidateQueries({ queryKey: ["/clients/"] }); },
  });
  async function submit(e) {
    e.preventDefault();
    const r = await action.run(form.values);
    if (r.ok) onConverted(r.data.client); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title="Convert to client" formId="convert-form" action={action} onClose={onClose} submitLabel="Convert to client">
      <form id="convert-form" onSubmit={submit}>
        <p className="muted">A client record is created from this lead. If a client with the same email already exists in this branch, the conversion is blocked.</p>
        <TextField form={form} name="contact_person" label="Contact person" />
        <TextAreaField form={form} name="address" label="Address" />
      </form>
    </FormDialog>
  );
}