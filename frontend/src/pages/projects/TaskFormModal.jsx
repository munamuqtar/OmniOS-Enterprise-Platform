import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { titleCase, todayIso } from "../../utils/format";
import FormDialog from "../../components/modals/FormDialog";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const PRIORITIES = ["low", "medium", "high", "urgent"].map((v) => ({ value: v, label: titleCase(v) }));

export default function TaskFormModal({ task, projectId, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({
    project: task?.project ?? projectId ?? "", title: task?.title ?? "", description: task?.description ?? "",
    assigned_employee: task?.assigned_employee ?? "", start_date: task?.start_date ?? "",
    due_date: task?.due_date ?? todayIso(14), priority: task?.priority ?? "medium",
  });
  const members = useDetail("/projects/", form.values.project, "members/");
  const save = useApiAction(
    async (body) => unwrap(task ? await api.put(`/tasks/${task.id}/`, body) : await api.post("/tasks/", body)),
    { onSuccess: () => { qc.invalidateQueries({ queryKey: ["/tasks/"] }); qc.invalidateQueries({ queryKey: ["/projects/"] }); } }
  );
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const r = await save.run({ project: v.project, title: v.title, description: v.description,
      assigned_employee: v.assigned_employee || null, start_date: v.start_date || null,
      due_date: v.due_date, priority: v.priority });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={task ? "Edit task" : "New task"} formId="task-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save task">
      <form id="task-form" onSubmit={submit}>
        {!(task || projectId) && (
          <LookupField form={form} name="project" label="Project" endpoint="/projects/" required
                       labelOf={(p) => `${p.project_code} · ${p.name}`} />
        )}
        <TextField form={form} name="title" label="Title" required />
        <TextAreaField form={form} name="description" label="Description" />
        <SelectField form={form} name="assigned_employee" label="Assignee" hint="Only project members can be assigned."
                     options={(members.data ?? []).map((m) => ({ value: m.employee, label: `${m.employee_name} (${m.employee_number})` }))} />
        <TextField form={form} name="start_date" label="Start date" type="date" />
        <TextField form={form} name="due_date" label="Due date" type="date" required />
        <SelectField form={form} name="priority" label="Priority" options={PRIORITIES} required />
      </form>
    </FormDialog>
  );
}
