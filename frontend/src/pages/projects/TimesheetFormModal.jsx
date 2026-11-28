import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { todayIso } from "../../utils/format";
import FormDialog from "../../components/modals/FormDialog";
import FormField from "../../components/forms/FormField";
import { SelectField, TextAreaField, TextField } from "../../components/forms/fields";

export default function TimesheetFormModal({ sheet, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({
    project: sheet?.project ?? "", task: sheet?.task ?? "", work_date: sheet?.work_date ?? todayIso(),
    hours: sheet?.hours ?? "", description: sheet?.description ?? "",
  });
  const projects = useQuery({
    queryKey: ["/projects/", "active-mine"],
    queryFn: async () => unwrap(await api.get("/projects/", { params: { status: "active" } })).results,
  });
  const tasks = useQuery({
    queryKey: ["/tasks/", "for", form.values.project], enabled: Boolean(form.values.project),
    queryFn: async () => unwrap(await api.get("/tasks/", { params: { project: form.values.project } })).results,
  });
  const save = useApiAction(
    async (body) => unwrap(sheet ? await api.put(`/timesheets/${sheet.id}/`, body) : await api.post("/timesheets/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/timesheets/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const r = await save.run(form.values);
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={sheet ? "Edit timesheet" : "New timesheet"} formId="sheet-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save timesheet">
      <form id="sheet-form" onSubmit={submit}>
        <FormField label="Project" required error={form.errors.project}>
          <select className="input" required value={form.values.project} aria-label="Project"
                  onChange={(e) => form.setValues((v) => ({ ...v, project: e.target.value, task: "" }))}>
            <option value="">— select —</option>
            {(projects.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.project_code} · {p.name}</option>)}
          </select>
        </FormField>
        <SelectField form={form} name="task" label="Task" required hint="Tasks assigned to you on this project."
                     options={(tasks.data ?? []).map((t) => ({ value: t.id, label: t.title }))} />
        <TextField form={form} name="work_date" label="Work date" type="date" max={todayIso()} required />
        <TextField form={form} name="hours" label="Hours" type="number" min="0.25" max="24" step="0.25" required />
        <TextAreaField form={form} name="description" label="What did you work on?" required />
      </form>
    </FormDialog>
  );
}
