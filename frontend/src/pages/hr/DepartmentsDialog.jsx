import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import Modal from "../../components/modals/Modal";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { TextAreaField, TextField } from "../../components/forms/fields";

const BLANK = { name: "", code: "", description: "" };

export default function DepartmentsDialog({ onClose }) {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["/departments/", "all"], queryFn: async () => unwrap(await api.get("/departments/")).results });
  const [editing, setEditing] = useState(null);                // null | "new" | department
  const form = useFormState(BLANK);
  const save = useApiAction(
    async ({ id, body }) => unwrap(id ? await api.put(`/departments/${id}/`, body) : await api.post("/departments/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/departments/"] }) }
  );
  const start = (dept) => {
    setEditing(dept ?? "new");
    form.reset(dept ? { name: dept.name, code: dept.code, description: dept.description } : BLANK);
  };
  async function submit(e) {
    e.preventDefault();
    const r = await save.run({ id: editing === "new" ? null : editing.id, body: form.values });
    if (r.ok) setEditing(null); else form.setErrors(r.error.fields);
  }

  return (
    <Modal title="Departments" onClose={onClose} footer={<button className="btn btn-ghost" onClick={onClose}>Close</button>}>
      {editing ? (
        <form onSubmit={submit}>
          <ErrorBanner message={save.error?.message} />
          <TextField form={form} name="name" label="Name" required />
          <TextField form={form} name="code" label="Code" required hint="A short unique code such as ENG." />
          <TextAreaField form={form} name="description" label="Description" />
          <div className="page-actions">
            <button className="btn btn-primary" disabled={save.busy}>Save department</button>
            <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </form>
      ) : (
        <>
          <button className="btn btn-primary" onClick={() => start(null)}>Add department</button>
          {list.data?.length ? (
            <ul className="activity space-top">
              {list.data.map((d) => (
                <li key={d.id}><strong>{d.name}</strong> ({d.code}) <button className="link" onClick={() => start(d)}>Edit</button></li>
              ))}
            </ul>
          ) : <EmptyState title="No departments yet" />}
        </>
      )}
    </Modal>
  );
}