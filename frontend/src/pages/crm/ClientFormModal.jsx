import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import Modal from "../../components/modals/Modal";
import ErrorBanner from "../../components/common/ErrorBanner";
import { SelectField, TextAreaField, TextField } from "../../components/forms/fields";

export default function ClientFormModal({ client, onClose, onSaved }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    name: client?.name ?? "", company_name: client?.company_name ?? "", contact_person: client?.contact_person ?? "",
    email: client?.email ?? "", phone: client?.phone ?? "", address: client?.address ?? "",
    status: client?.status ?? "active", branch: client?.branch ?? (branches.length === 1 ? branches[0].id : ""),
  });
  const save = useApiAction(
    async (body) => unwrap(client ? await api.put(`/clients/${client.id}/`, body) : await api.post("/clients/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/clients/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const r = await save.run(form.values);
    if (r.ok) onSaved(r.data); else form.setErrors(r.error.fields);
  }
  return (
    <Modal title={client ? "Edit client" : "New client"} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="client-form" disabled={save.busy}>{save.busy ? "Saving…" : "Save client"}</button>
      </>
    }>
      <form id="client-form" onSubmit={submit}>
        <ErrorBanner message={save.error?.message} />
        <TextField form={form} name="name" label="Client name" required />
        <TextField form={form} name="company_name" label="Company" />
        <TextField form={form} name="contact_person" label="Contact person" />
        <TextField form={form} name="email" label="Email" type="email" required />
        <TextField form={form} name="phone" label="Phone" />
        <TextAreaField form={form} name="address" label="Address" />
        <SelectField form={form} name="branch" label="Branch" required
                     options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        {client && <SelectField form={form} name="status" label="Status"
                                options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />}
      </form>
    </Modal>
  );
}