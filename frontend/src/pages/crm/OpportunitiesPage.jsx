import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useFormState } from "../../hooks/useFormState";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate, formatNumber, titleCase, todayIso } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import DataTable from "../../components/tables/DataTable";
import Modal from "../../components/modals/Modal";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const STAGES = ["prospecting", "qualification", "proposal", "negotiation", "won", "lost"]
  .map((value) => ({ value, label: titleCase(value) }));

function OpportunityForm({ opp, onClose }) {
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    name: opp?.name ?? "", client: opp?.client ?? "", lead: opp?.lead ?? "",
    branch: opp?.branch ?? (branches.length === 1 ? branches[0].id : ""),
    value: opp?.value ?? "", probability: opp?.probability ?? 10,
    expected_close_date: opp?.expected_close_date ?? todayIso(30), notes: opp?.notes ?? "",
  });
  const save = useApiAction(
    async (body) => unwrap(opp ? await api.put(`/opportunities/${opp.id}/`, body) : await api.post("/opportunities/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/opportunities/"] }) }
  );
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    if (!v.client && !v.lead) { form.setErrors({ client: "Select a client or a lead." }); return; }
    const r = await save.run({ ...v, client: v.client || null, lead: v.lead || null });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <Modal title={opp ? "Edit opportunity" : "New opportunity"} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="opp-form" disabled={save.busy}>{save.busy ? "Saving…" : "Save"}</button>
      </>
    }>
      <form id="opp-form" onSubmit={submit}>
        <ErrorBanner message={save.error?.message} />
        <TextField form={form} name="name" label="Name" required />
        <LookupField form={form} name="client" label="Client" endpoint="/clients/" initialLabel={opp?.client_name} />
        <LookupField form={form} name="lead" label="Lead" endpoint="/leads/" initialLabel={opp?.lead_name}
                     hint="Pick a client or a lead." />
        <SelectField form={form} name="branch" label="Branch" required
                     options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        <TextField form={form} name="value" label="Expected value" type="number" min="0" step="0.01" required />
        <TextField form={form} name="probability" label="Probability (%)" type="number" min="0" max="100" required />
        <TextField form={form} name="expected_close_date" label="Expected close date" type="date" required />
        <TextAreaField form={form} name="notes" label="Notes" />
      </form>
    </Modal>
  );
}

function StageDialog({ opp, onClose }) {
  const qc = useQueryClient();
  const form = useFormState({ stage: "", reason: "" });
  const action = useApiAction(async (body) => unwrap(await api.post(`/opportunities/${opp.id}/stage/`, body)),
                              { onSuccess: () => qc.invalidateQueries({ queryKey: ["/opportunities/"] }) });
  async function submit(e) {
    e.preventDefault();
    const r = await action.run({ stage: form.values.stage, reason: form.values.reason });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <Modal title={`Change stage: ${opp.name}`} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="stage-form" disabled={action.busy || !form.values.stage}>Update stage</button>
      </>
    }>
      <form id="stage-form" onSubmit={submit}>
        <ErrorBanner message={action.error?.message} />
        <p className="muted">Stages move one step forward at a time. You can go back, and an opportunity can be marked lost from any open stage.</p>
        <SelectField form={form} name="stage" label="New stage" required
                     options={STAGES.filter((s) => s.value !== opp.stage)} />
        {form.values.stage === "lost" && <TextAreaField form={form} name="reason" label="Why was it lost?" required />}
      </form>
    </Modal>
  );
}

function PipelineTiles({ filters }) {
  const q = useQuery({
    queryKey: ["/opportunities/", "pipeline", filters],
    queryFn: async () => unwrap(await api.get("/opportunities/pipeline/", { params: filters })),
  });
  return (
    <div className="stage-tiles">
      {(q.data ?? []).map((s) => (
        <div key={s.stage} className="kpi">
          <span className="muted">{titleCase(s.stage)}</span>
          <strong>{s.count}</strong>
          <small className="muted">{formatNumber(s.value)}</small>
        </div>
      ))}
    </div>
  );
}

export default function OpportunitiesPage() {
  const list = usePaginatedList("/opportunities/");
  const branches = useBranchOptions();
  const [editing, setEditing] = useState(null);       // null | "new" | opportunity
  const [staging, setStaging] = useState(null);
  const stop = (fn) => (e) => { e.stopPropagation(); fn(); };

  const columns = [
    { key: "name", header: "Opportunity" },
    { key: "party", header: "Client / lead", render: (r) => r.client_name || r.lead_name || "—" },
    { key: "value", header: "Value", render: (r) => formatNumber(r.value) },
    { key: "probability", header: "Probability", render: (r) => `${r.probability}%` },
    { key: "expected_close_date", header: "Expected close", render: (r) => formatDate(r.expected_close_date) },
    { key: "stage", header: "Stage", render: (r) => <StatusBadge status={r.stage} /> },
    { key: "actions", header: "", render: (r) => !["won", "lost"].includes(r.stage) && (
      <div className="page-actions">
        <button className="btn btn-ghost" onClick={stop(() => setEditing(r))}>Edit</button>
        <button className="btn btn-ghost" onClick={stop(() => setStaging(r))}>Change stage</button>
      </div>
    ) },
  ];

  return (
    <>
      <PageHeader title="Opportunities" subtitle="Your sales pipeline"
                  actions={<button className="btn btn-primary" onClick={() => setEditing("new")}>New opportunity</button>} />
      <PipelineTiles filters={list.filters} />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search opportunities…" />
        <FilterSelect label="Stage" allLabel="All stages" value={list.filters.stage ?? ""}
                      onChange={(v) => list.setFilter("stage", v)} options={STAGES} />
        {branches.length > 1 && (
          <FilterSelect label="Branch" allLabel="All branches" value={list.filters.branch ?? ""}
                        onChange={(v) => list.setFilter("branch", v)}
                        options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        )}
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 emptyTitle="No opportunities yet" emptyHint="Create one from a client or a qualified lead."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {editing && <OpportunityForm opp={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      {staging && <StageDialog opp={staging} onClose={() => setStaging(null)} />}
    </>
  );
}