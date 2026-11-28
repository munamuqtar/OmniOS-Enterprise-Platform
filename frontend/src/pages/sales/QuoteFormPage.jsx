import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useApiAction } from "../../hooks/useApiAction";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useDetail } from "../../hooks/useDetail";
import { useFormState } from "../../hooks/useFormState";
import { calcTotals } from "../../utils/money";
import { parseApiError } from "../../utils/errors";
import { formatMoney, todayIso } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import ErrorBanner from "../../components/common/ErrorBanner";
import EmptyState from "../../components/common/EmptyState";
import { Spinner } from "../../components/common/Spinner";
import { LookupField, SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const blankItem = () => ({ description: "", quantity: "1", unit_price: "" });

function QuoteForm({ quote, presetClient }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const branches = useBranchOptions();
  const form = useFormState({
    client: quote?.client ?? presetClient?.id ?? "", lead: quote?.lead ?? "",
    branch: quote?.branch ?? (branches.length === 1 ? branches[0].id : ""),
    currency: quote?.currency ?? "USD", valid_until: quote?.valid_until ?? todayIso(30),
    payment_terms: quote?.payment_terms ?? "", notes: quote?.notes ?? "",
    discount: quote?.discount ?? "0", tax_rate: quote?.tax_rate ?? "0",
  });
  const [items, setItems] = useState(
    quote?.items?.length
      ? quote.items.map((i) => ({ description: i.description, quantity: i.quantity, unit_price: i.unit_price }))
      : [blankItem()]
  );
  const totals = calcTotals(items, form.values.discount, form.values.tax_rate);
  const currency = form.values.currency || "USD";
  const save = useApiAction(
    async (body) => unwrap(quote ? await api.put(`/quotes/${quote.id}/`, body) : await api.post("/quotes/", body)),
    { onSuccess: () => qc.invalidateQueries({ queryKey: ["/quotes/"] }) }
  );
  const setItem = (i, key, value) => setItems((rows) => rows.map((r, n) => (n === i ? { ...r, [key]: value } : r)));

  async function submit(e) {
    e.preventDefault();
    const v = form.values;
    if (!v.client && !v.lead) { form.setErrors({ client: "Select a client or a lead." }); return; }
    const r = await save.run({
      client: v.client || null, lead: v.lead || null, branch: v.branch, currency: currency.toUpperCase(),
      valid_until: v.valid_until, payment_terms: v.payment_terms, notes: v.notes,
      discount: v.discount || "0", tax_rate: v.tax_rate || "0", items,
    });
    if (r.ok) navigate(`/sales/quotations/${r.data.id}`); else form.setErrors(r.error.fields);
  }

  return (
    <form onSubmit={submit}>
      <ErrorBanner message={save.error?.message} />
      <div className="section-grid">
        <section className="card">
          <h3>Customer</h3>
          <LookupField form={form} name="client" label="Client" endpoint="/clients/" initialLabel={quote?.client_name ?? presetClient?.name} />
          <LookupField form={form} name="lead" label="Lead" endpoint="/leads/" initialLabel={quote?.lead_name}
                       hint="Pick a client, or a lead if the customer is not converted yet." />
          <SelectField form={form} name="branch" label="Branch" required
                       options={branches.map((b) => ({ value: b.id, label: b.name }))} />
        </section>
        <section className="card">
          <h3>Terms</h3>
          <TextField form={form} name="currency" label="Currency" maxLength={3} required />
          <TextField form={form} name="valid_until" label="Valid until" type="date" required />
          <TextField form={form} name="payment_terms" label="Payment terms" />
          <TextAreaField form={form} name="notes" label="Notes" />
        </section>
      </div>

      <section className="card panel-gap">
        <h3>Items</h3>
        {form.errors.items && <p className="error-text" role="alert">{form.errors.items}</p>}
        <div className="items-editor">
          <div className="items-head"><span>Description</span><span>Qty</span><span>Unit price</span><span>Line total</span><span /></div>
          {items.map((it, i) => (
            <div className="items-row" key={i}>
              <input className="input" aria-label={`Description ${i + 1}`} value={it.description} required
                     onChange={(e) => setItem(i, "description", e.target.value)} />
              <input className="input" aria-label={`Quantity ${i + 1}`} type="number" min="0.01" step="0.01" value={it.quantity} required
                     onChange={(e) => setItem(i, "quantity", e.target.value)} />
              <input className="input" aria-label={`Unit price ${i + 1}`} type="number" min="0" step="0.01" value={it.unit_price} required
                     onChange={(e) => setItem(i, "unit_price", e.target.value)} />
              <span>{formatMoney(totals.lines[i], currency)}</span>
              <button type="button" className="btn btn-ghost" disabled={items.length === 1}
                      onClick={() => setItems((rows) => rows.filter((_, n) => n !== i))}>Remove</button>
            </div>
          ))}
        </div>
        <button type="button" className="btn btn-ghost" onClick={() => setItems((rows) => [...rows, blankItem()])}>Add item</button>

        <div className="totals">
          <TextField form={form} name="discount" label="Discount (amount)" type="number" min="0" step="0.01" />
          <TextField form={form} name="tax_rate" label="Tax rate (%)" type="number" min="0" max="100" step="0.01" />
          <dl className="info-grid">
            <div><dt>Subtotal</dt><dd>{formatMoney(totals.subtotal, currency)}</dd></div>
            <div><dt>Tax</dt><dd>{formatMoney(totals.tax, currency)}</dd></div>
            <div><dt>Total (estimate)</dt><dd><strong>{formatMoney(totals.total, currency)}</strong></dd></div>
          </dl>
          {totals.discountTooHigh && <p className="error-text" role="alert">The discount cannot be more than the subtotal.</p>}
          <small className="muted">The server calculates the final totals when you save.</small>
        </div>
      </section>

      <div className="page-actions">
        <Link className="btn btn-ghost" to={quote ? `/sales/quotations/${quote.id}` : "/sales/quotations"}>Cancel</Link>
        <button className="btn btn-primary" disabled={save.busy}>{save.busy ? "Saving…" : "Save quotation"}</button>
      </div>
    </form>
  );
}

export default function QuoteFormPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const existing = useDetail("/quotes/", id);

  if (existing.isLoading) return <Spinner />;
  if (existing.error) return <ErrorBanner message={parseApiError(existing.error).message} onRetry={existing.refetch} />;
  const q = existing.data;
  if (q && !["draft", "rejected"].includes(q.status)) {
    return (
      <EmptyState title="This quotation cannot be edited" hint="Only draft or rejected quotations can be changed. Approved quotes must be reopened for revision first.">
        <Link className="btn btn-primary" to={`/sales/quotations/${q.id}`}>Back to the quotation</Link>
      </EmptyState>
    );
  }
  const preset = params.get("client") ? { id: params.get("client"), name: params.get("name") } : null;
  return (
    <>
      <PageHeader title={q ? `Edit ${q.quote_number}` : "New quotation"} />
      <QuoteForm key={q?.id ?? "new"} quote={q} presetClient={preset} />
    </>
  );
}