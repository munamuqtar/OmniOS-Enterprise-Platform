import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { MULTIPART, toFormData } from "../../utils/forms";
import { parseApiError } from "../../utils/errors";
import PageHeader from "../../components/common/PageHeader";
import ErrorBanner from "../../components/common/ErrorBanner";
import { Spinner } from "../../components/common/Spinner";
import { FileField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

function OrganizationForm({ org }) {
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  const form = useFormState({
    name: org?.name ?? "", company_code: org?.company_code ?? "", email: org?.email ?? "",
    phone: org?.phone ?? "", address: org?.address ?? "", status: org?.status ?? "active", logo: null,
  });
  const save = useApiAction(
    async (fd) => unwrap(org ? await api.put(`/organizations/${org.id}/`, fd, MULTIPART) : await api.post("/organizations/", fd, MULTIPART)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/organizations/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    setSaved(false);
    const r = await save.run(toFormData(form.values));
    if (r.ok) { setSaved(true); form.setValues((v) => ({ ...v, logo: null })); } else form.setErrors(r.error.fields);
  }
  return (
    <form onSubmit={submit} className="card narrow">
      <ErrorBanner message={save.error?.message} />
      {saved && <div className="banner success">Saved.</div>}
      {org?.logo && <img className="logo-preview" src={org.logo} alt="Company logo" />}
      <TextField form={form} name="name" label="Company name" required />
      <TextField form={form} name="company_code" label="Company code" required hint="Short and unique, for example HZN." />
      <TextField form={form} name="email" label="Email" type="email" />
      <TextField form={form} name="phone" label="Phone" />
      <TextAreaField form={form} name="address" label="Address" />
      <SelectField form={form} name="status" label="Status" options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} required />
      <FileField form={form} name="logo" label="Logo" accept="image/png,image/jpeg" maxMb={2} hint="PNG or JPEG, up to 2 MB." />
      <button className="btn btn-primary" disabled={save.busy}>{save.busy ? "Saving…" : org ? "Save changes" : "Create company"}</button>
    </form>
  );
}

export default function OrganizationPage() {
  const q = useQuery({
    queryKey: ["/organizations/", "first"],
    queryFn: async () => unwrap(await api.get("/organizations/")).results[0] ?? null,
  });
  return (
    <>
      <PageHeader title="Organization" subtitle="Your company's details" />
      {q.isLoading ? <Spinner /> : q.error
        ? <ErrorBanner message={parseApiError(q.error).message} onRetry={q.refetch} />
        : <OrganizationForm key={q.data?.id ?? "new"} org={q.data} />}
    </>
  );
}