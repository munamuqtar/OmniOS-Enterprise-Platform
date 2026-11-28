import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import { MULTIPART, toFormData } from "../../utils/forms";
import FormDialog from "../../components/modals/FormDialog";
import { FileField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

export default function CandidateFormModal({ candidate, onClose, onSaved }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    first_name: candidate?.first_name ?? "", last_name: candidate?.last_name ?? "", email: candidate?.email ?? "",
    phone: candidate?.phone ?? "", source: candidate?.source ?? "", summary: candidate?.summary ?? "",
    branch: candidate?.branch ?? (branches.length === 1 ? branches[0].id : ""), resume: null,
  });
  const save = useApiAction(
    async (fd) => unwrap(candidate ? await api.put(`/candidates/${candidate.id}/`, fd, MULTIPART) : await api.post("/candidates/", fd, MULTIPART)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/candidates/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const r = await save.run(toFormData(form.values));
    if (r.ok) onSaved(r.data); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={candidate ? "Edit candidate" : "New candidate"} formId="candidate-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save candidate">
      <form id="candidate-form" onSubmit={submit}>
        <TextField form={form} name="first_name" label="First name" required />
        <TextField form={form} name="last_name" label="Last name" required />
        <TextField form={form} name="email" label="Email" type="email" required />
        <TextField form={form} name="phone" label="Phone" />
        <SelectField form={form} name="branch" label="Branch" required options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <TextField form={form} name="source" label="Source" hint="Website, referral, job fair…" />
        <TextAreaField form={form} name="summary" label="Summary" />
        <FileField form={form} name="resume" label="Resume" accept=".pdf,.doc,.docx" maxMb={5}
                   hint={candidate?.resume ? "Choose a file only to replace the current resume. PDF or Word, up to 5 MB." : "PDF or Word, up to 5 MB."} />
      </form>
    </FormDialog>
  );
}