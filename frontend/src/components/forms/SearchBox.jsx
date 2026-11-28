export default function SearchBox({ value, onChange, placeholder = "Search…" }) {
  return (
    <input className="input search" type="search" value={value} placeholder={placeholder}
           aria-label="Search" onChange={(e) => onChange(e.target.value)} />
  );
}

export function FilterSelect({ label, value, onChange, options, allLabel }) {
  return (
    <select className="input" aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{allLabel ?? `All ${label.toLowerCase()}`}</option>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}