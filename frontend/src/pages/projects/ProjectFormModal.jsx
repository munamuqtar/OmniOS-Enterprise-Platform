import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import { todayIso } from "../../utils/format";
import FormDialog from "../../components/modals/FormDialog";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

export default function ProjectFormModal({ project, onClose, onSaved }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    name: project?.name ?? "", client: project?.client ?? "", manager: project?.manager ?? "",
    branch: project?.branch ?? (branches.length === 1 ? branches[0].id : ""), description: project?.description ?? "",
    start_date: project?.start_date ?? todayIso(), end_date: project?.end_date ?? todayIso(90), budget: project?.budget ?? "",
  });
  const save = useApiAction(
    async (body) => unwrap(project ? await api.put(`/projects/${project.id}/`, body) : await api.post("/projects/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/projects/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const r = await save.run({ ...form.values, budget: form.values.budget || null });
    if (r.ok) onSaved(r.data); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={project ? "Edit project" : "New project"} formId="project-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save project">
      <form id="project-form" onSubmit={submit}>
        <TextField form={form} name="name" label="Project name" required />
        <LookupField form={form} name="client" label="Client" endpoint="/clients/" required initialLabel={project?.client_name} />
        <SelectField form={form} name="branch" label="Branch" required
                     options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <LookupField form={form} name="manager" label="Project manager" endpoint="/lookups/users/" required
                     params={{ role: "project_manager" }} labelOf={(u) => u.name} initialLabel={project?.manager_name} />
        <TextAreaField form={form} name="description" label="Description" />
        <TextField form={form} name="start_date" label="Start date" type="date" required />
        <TextField form={form} name="end_date" label="End date" type="date" required />
        <TextField form={form} name="budget" label="Budget (optional)" type="number" min="0" step="0.01" />
      </form>
    </FormDialog>
  );
}
