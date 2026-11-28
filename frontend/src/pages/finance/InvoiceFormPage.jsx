import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { calcTotals } from "../../utils/money";
import { formatDate, formatMoney, formatNumber, todayIso } from "../../utils/format";
import { groupHoursByTask } from "../../utils/workflow";
import PageHeader from "../../components/common/PageHeader";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import { LookupField, TextAreaField, TextField } from "../../components/forms/fields";

export default function InvoiceFormPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const form = useFormState({ project: "", currency: "USD", hourly_rate: "", tax_rate: "0", discount: "0",
                              issue_date: todayIso(), due_date: todayIso(30), notes: "" });
  const [selection, setSelection] = useState({ project: "", ids: {} });
  const projectId = form.values.project;
  const billable = useQuery({
    queryKey: ["/invoices/", "billable", projectId], enabled: Boolean(projectId),
    queryFn: async () => unwrap(await api.get("/invoices/billable/", { params: { project: projectId } })),
  });
  const rows = billable.data?.timesheets ?? [];
  const ids = selection.project === projectId ? selection.ids : {};      // selection resets when the project changes
  const chosen = rows.filter((r) => ids[r.id]);
  const toggle = (id) => setSelection({ project: projectId, ids: { ...ids, [id]: !ids[id] } });
  const toggleAll = () => setSelection({
    project: projectId, ids: chosen.length === rows.length ? {} : Object.fromEntries(rows.map((r) => [r.id, true])),
  });
  const items = groupHoursByTask(chosen).map((g) => ({ quantity: g.hours, unit_price: form.values.hourly_rate }));
  const totals = calcTotals(items, form.values.discount, form.values.tax_rate);
  const hours = chosen.reduce((a, r) => a + Number(r.hours), 0);
  const currency = form.values.currency || "USD";

  const save = useApiAction(async (body) => unwrap(await api.post("/invoices/", body)),
                            { onSuccess: () => qc.invalidateQueries({ queryKey: ["/invoices/"] }) });
  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    const r = await save.run({ project: v.project, currency: currency.toUpperCase(), hourly_rate: v.hourly_rate,
      tax_rate: v.tax_rate || "0", discount: v.discount || "0", issue_date: v.issue_date, due_date: v.due_date,
      notes: v.notes, timesheet_ids: chosen.map((c) => c.id) });
    if (r.ok) { qc.invalidateQueries({ queryKey: ["/timesheets/"] }); navigate(`/finance/invoices/${r.data.id}`); }
    else form.setErrors(r.error.fields);
  }

  return (
    <>
      <PageHeader title="New invoice" subtitle="Pick approved, unbilled work from a project" />
      <form onSubmit={submit}>
        <ErrorBanner message={save.error?.message} />
        <div className="section-grid">
          <section className="card">
            <h3>Project</h3>
            <LookupField form={form} name="project" label="Project" endpoint="/projects/" required
                         labelOf={(p) => `${p.project_code} · ${p.name}`} />
            <TextField form={form} name="issue_date" label="Issue date" type="date" required />
            <TextField form={form} name="due_date" label="Due date" type="date" required />
          </section>
          <section className="card">
            <h3>Pricing</h3>
            <TextField form={form} name="currency" label="Currency" maxLength={3} required />
            <TextField form={form} name="hourly_rate" label="Hourly rate" type="number" min="0.01" step="0.01" required />
            <TextField form={form} name="discount" label="Discount (amount)" type="number" min="0" step="0.01" />
            <TextField form={form} name="tax_rate" label="Tax rate (%)" type="number" min="0" max="100" step="0.01" />
          </section>
        </div>

        <section className="card panel-gap">
          <h3>Approved work</h3>
          {form.errors.timesheet_ids && <p className="error-text" role="alert">{form.errors.timesheet_ids}</p>}
          {!projectId ? <EmptyState title="Choose a project" hint="Approved, unbilled timesheets will be listed here." />
            : billable.isLoading ? <Spinner />
            : rows.length === 0 ? <EmptyState title="Nothing to bill" hint="This project has no approved timesheets waiting for an invoice." />
            : (
              <div className="table-scroll">
                <table>
                  <thead><tr>
                    <th><input type="checkbox" aria-label="Select all" checked={chosen.length === rows.length} onChange={toggleAll} /></th>
                    <th>Date</th><th>Employee</th><th>Task</th><th>Hours</th>
                  </tr></thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id}>
                        <td><input type="checkbox" aria-label={`Select ${r.task} on ${r.work_date}`} checked={Boolean(ids[r.id])} onChange={() => toggle(r.id)} /></td>
                        <td>{formatDate(r.work_date)}</td><td>{r.employee}</td><td>{r.task}</td><td>{formatNumber(r.hours)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          <div className="totals">
            <dl className="info-grid">
              <div><dt>Selected hours</dt><dd>{formatNumber(hours)}</dd></div>
              <div><dt>Subtotal</dt><dd>{formatMoney(totals.subtotal, currency)}</dd></div>
              <div><dt>Tax</dt><dd>{formatMoney(totals.tax, currency)}</dd></div>
              <div><dt>Total (estimate)</dt><dd><strong>{formatMoney(totals.total, currency)}</strong></dd></div>
            </dl>
            {totals.discountTooHigh && <p className="error-text" role="alert">The discount cannot be more than the subtotal.</p>}
            <small className="muted">The server calculates the final totals. Billed hours cannot be invoiced twice.</small>
          </div>
          <TextAreaField form={form} name="notes" label="Notes" />
        </section>

        <div className="page-actions">
          <Link className="btn btn-ghost" to="/finance/invoices">Cancel</Link>
          <button className="btn btn-primary" disabled={save.busy || chosen.length === 0}>{save.busy ? "Creating…" : "Create draft invoice"}</button>
        </div>
      </form>
    </>
  );
}
