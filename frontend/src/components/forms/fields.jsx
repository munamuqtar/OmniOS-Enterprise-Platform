import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import FormField from "./FormField";

export function TextField({ form, name, label, type = "text", required, hint, ...rest }) {
  return (
    <FormField label={label} required={required} hint={hint} error={form.errors[name]}>
      <input className="input" type={type} required={required} value={form.values[name] ?? ""}
             onChange={(e) => form.set(name, e.target.value)} {...rest} />
    </FormField>
  );
}

export function TextAreaField({ form, name, label, rows = 3, required, hint }) {
  return (
    <FormField label={label} required={required} hint={hint} error={form.errors[name]}>
      <textarea className="input" rows={rows} required={required} value={form.values[name] ?? ""}
                onChange={(e) => form.set(name, e.target.value)} />
    </FormField>
  );
}

export function SelectField({ form, name, label, options, required, hint, placeholder = "— select —" }) {
  return (
    <FormField label={label} required={required} hint={hint} error={form.errors[name]}>
      <select className="input" required={required} value={form.values[name] ?? ""}
              onChange={(e) => form.set(name, e.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </FormField>
  );
}

/** Search box plus a list of matches from the API; stores the chosen record's id. */
export function LookupField({ form, name, label, endpoint, params = {}, labelOf = (r) => r.name,
                              required, hint, initialLabel }) {
  const [text, setText] = useState("");
  const q = useQuery({
    queryKey: [endpoint, "lookup", text, params], staleTime: 30000,
    queryFn: async () => {
      const body = unwrap(await api.get(endpoint, { params: { ...params, search: text || undefined } }));
      return body.results ?? body;
    },
  });


  
  const current = form.values[name];
  const rows = q.data ?? [];
  const missing = current && !rows.some((r) => r.id === current);
  const error = form.errors[name];

  return (
    <div className={`field ${error ? "has-error" : ""}`}>
      <span>{label}{required && <b aria-hidden="true"> *</b>}</span>
      <input className="input" aria-label={`Search ${label}`} placeholder="Type to search…"
             value={text} onChange={(e) => setText(e.target.value)} />
      <select className="input" aria-label={label} required={required} value={current ?? ""}
              onChange={(e) => form.set(name, e.target.value)}>
        <option value="">— none —</option>
        {missing && <option value={current}>{initialLabel ?? "Current selection"}</option>}
        {rows.map((r) => <option key={r.id} value={r.id}>{labelOf(r)}</option>)}
      </select>
      {hint && !error && <small className="muted">{hint}</small>}
      {error && <small className="error-text" role="alert">{error}</small>}
    </div>
  );
}

export function CheckboxGroup({ form, name, label, options, hint }) {
  const selected = form.values[name] ?? [];
  const toggle = (value) =>
    form.set(name, selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  return (
    <fieldset className={`field checks ${form.errors[name] ? "has-error" : ""}`}>
      <legend>{label}</legend>
      {options.map((o) => (
        <label key={o.value} className="check">
          <input type="checkbox" checked={selected.includes(o.value)} onChange={() => toggle(o.value)} /> {o.label}
        </label>
      ))}
      {hint && !form.errors[name] && <small className="muted">{hint}</small>}
      {form.errors[name] && <small className="error-text" role="alert">{form.errors[name]}</small>}
    </fieldset>
  );
}

export function FileField({ form, name, label, accept, hint, maxMb }) {
  return (
    <FormField label={label} hint={hint} error={form.errors[name]}>
      <input className="input" type="file" accept={accept} onChange={(e) => {
        const file = e.target.files?.[0] ?? null;
        if (file && maxMb && file.size > maxMb * 1024 * 1024) {
          form.setErrors({ ...form.errors, [name]: `The file must be ${maxMb} MB or smaller.` });
          e.target.value = "";
          return;
        }
        form.set(name, file);
      }} />
    </FormField>
  );
}