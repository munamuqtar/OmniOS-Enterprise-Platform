import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import Modal from "../../components/modals/Modal";
import ErrorBanner from "../../components/common/ErrorBanner";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

export default function LeadFormModal({ lead, onClose, onSaved }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    name: lead?.name ?? "", company_name: lead?.company_name ?? "", email: lead?.email ?? "",
    phone: lead?.phone ?? "", source: lead?.source ?? "", notes: lead?.notes ?? "", owner: lead?.owner ?? "",
    branch: lead?.branch ?? (branches.length === 1 ? branches[0].id : ""),
  });
  const save = useApiAction(
    async (body) => unwrap(lead ? await api.put(`/leads/${lead.id}/`, body) : await api.post("/leads/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/leads/"] }) }
  );

  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const body = { name: v.name, company_name: v.company_name, email: v.email, phone: v.phone,
                   source: v.source, notes: v.notes, branch: v.branch };
    if (v.owner) body.owner = v.owner;
    const r = await save.run(body);
    if (r.ok) onSaved(r.data); else form.setErrors(r.error.fields);
  }

  return (
    <Modal title={lead ? "Edit lead" : "New lead"} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" onClick={onClose} type="button">Cancel</button>
        <button className="btn btn-primary" form="lead-form" disabled={save.busy}>{save.busy ? "Saving…" : "Save lead"}</button>
      </>
    }>
      <form id="lead-form" onSubmit={submit}>
        <ErrorBanner message={save.error?.message} />
        <TextField form={form} name="name" label="Contact name" required />
        <TextField form={form} name="company_name" label="Company" />
        <TextField form={form} name="email" label="Email" type="email" required />
        <TextField form={form} name="phone" label="Phone" />
        <TextField form={form} name="source" label="Source" hint="Website, referral, event…" />
        <SelectField form={form} name="branch" label="Branch" required
                     options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <LookupField form={form} name="owner" label="Salesperson" endpoint="/lookups/users/" params={{ role: "sales" }}
                     labelOf={(u) => u.name} initialLabel={lead?.owner_name} hint="Leave empty to assign it to yourself." />
        <TextAreaField form={form} name="notes" label="Notes" />
      </form>
    </Modal>
  );
}