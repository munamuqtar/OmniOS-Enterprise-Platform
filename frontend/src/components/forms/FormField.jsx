export default function FormField({ label, error, hint, required, children }) {
  return (
    <label className={`field ${error ? "has-error" : ""}`}>
      <span>{label}{required && <b aria-hidden="true"> *</b>}</span>
      {children}
      {hint && !error && <small className="muted">{hint}</small>}
      {error && <small className="error-text" role="alert">{error}</small>}
    </label>
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