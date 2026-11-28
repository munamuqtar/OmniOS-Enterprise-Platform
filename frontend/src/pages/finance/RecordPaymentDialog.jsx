import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { useFormState } from "../../hooks/useFormState";
import { formatMoney, titleCase, todayIso } from "../../utils/format";
import FormDialog from "../../components/modals/FormDialog";
import { SelectField, TextAreaField, TextField } from "../../components/forms/fields";

const METHODS = ["bank_transfer", "cash", "mobile_money", "card", "cheque"].map((v) => ({ value: v, label: titleCase(v) }));

export default function RecordPaymentDialog({ invoice, onClose }) {
  const qc = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const form = useFormState({ amount: invoice.balance, method: "bank_transfer", reference: "", payment_date: todayIso(),
                              notes: "", initial_status: "confirmed", allow_overpayment: false });
  const save = useApiAction(async (body) => unwrap(await api.post("/payments/", body)), {
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["/invoices/"] }); qc.invalidateQueries({ queryKey: ["/payments/"] }); },
  });
  async function submit(e) {
    e.preventDefault();
    const r = await save.run({ ...form.values, invoice: invoice.id, allow_overpayment: isSuperAdmin && form.values.allow_overpayment });
    if (r.ok) onClose(); else form.setErrors(r.error.fields);
  }
  return (
    <FormDialog title={`Record payment for ${invoice.invoice_number}`} formId="payment-form" busy={save.busy}
                error={save.error?.message} onClose={onClose} submitLabel="Record payment">
      <form id="payment-form" onSubmit={submit}>
        <p className="muted">Outstanding balance: <strong>{formatMoney(invoice.balance, invoice.currency)}</strong>. Payments are simulated records, no real money moves.</p>
        <TextField form={form} name="amount" label="Amount" type="number" min="0.01" step="0.01" required />
        <SelectField form={form} name="method" label="Method" options={METHODS} required />
        <TextField form={form} name="reference" label="Transaction reference" required />
        <TextField form={form} name="payment_date" label="Payment date" type="date" max={todayIso()} required />
        <SelectField form={form} name="initial_status" label="Status"
                     options={[{ value: "confirmed", label: "Confirmed (counts now)" }, { value: "pending", label: "Pending (awaiting confirmation)" }]} required />
        <TextAreaField form={form} name="notes" label="Notes" />
        {isSuperAdmin && (
          <label className="check">
            <input type="checkbox" checked={form.values.allow_overpayment} onChange={(e) => form.set("allow_overpayment", e.target.checked)} />
            Authorize an overpayment (Super Admin only)
          </label>
        )}
      </form>
    </FormDialog>
  );
}
