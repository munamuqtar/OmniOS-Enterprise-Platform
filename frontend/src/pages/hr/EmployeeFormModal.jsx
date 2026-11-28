import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useDepartments } from "../../hooks/useDepartments";
import { useFormState } from "../../hooks/useFormState";
import { todayIso } from "../../utils/format";
import FormDialog from "../../components/modals/FormDialog";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";
import { EMPLOYEE_STATUSES } from "../../utils/constants";



export default function EmployeeFormModal({ employee, onClose, onSaved }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const departments = useDepartments();
  const form = useFormState({
    employee_number: employee?.employee_number ?? "", first_name: employee?.first_name ?? "",
    last_name: employee?.last_name ?? "", email: employee?.email ?? "", phone: employee?.phone ?? "",
    address: employee?.address ?? "", department: employee?.department ?? "", position: employee?.position ?? "",
    branch: employee?.branch ?? (branches.length === 1 ? branches[0].id : ""),
    hire_date: employee?.hire_date ?? todayIso(), status: employee?.status ?? "active", user: employee?.user ?? "",
  });
  const save = useApiAction(
    async (body) => unwrap(employee ? await api.put(`/employees/${employee.id}/`, body) : await api.post("/employees/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/employees/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const r = await save.run({ ...v, employee_number: v.employee_number || undefined,
                               department: v.department || null, user: v.user || null });
    if (r.ok) onSaved(r.data); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={employee ? "Edit employee" : "New employee"} formId="employee-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Save employee">
      <form id="employee-form" onSubmit={submit}>
        <TextField form={form} name="employee_number" label="Employee number" hint="Leave empty to generate one." />
        <TextField form={form} name="first_name" label="First name" required />
        <TextField form={form} name="last_name" label="Last name" required />
        <TextField form={form} name="email" label="Email" type="email" required />
        <TextField form={form} name="phone" label="Phone" />
        <TextAreaField form={form} name="address" label="Address" rows={2} />
        <SelectField form={form} name="department" label="Department"
                     options={departments.map((d) => ({ value: d.id, label: d.name }))} />
        <TextField form={form} name="position" label="Position" />
        <SelectField form={form} name="branch" label="Branch" required
                     options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <TextField form={form} name="hire_date" label="Hire date" type="date" required />
        {employee && <SelectField form={form} name="status" label="Employment status" options={EMPLOYEE_STATUSES} required />}
        <LookupField form={form} name="user" label="Login account" endpoint="/lookups/users/" params={{ unlinked: 1 }}
                     labelOf={(u) => `${u.name} (${u.username})`} initialLabel={employee?.user_name}
                     hint="Link the person's user account so they can log time and see their own work." />
      </form>
    </FormDialog>
  );
}