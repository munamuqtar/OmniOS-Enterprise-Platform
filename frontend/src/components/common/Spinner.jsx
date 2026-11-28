export function Spinner({ label = "Loading…" }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function FullPageSpinner() {
  return <div className="fullpage"><Spinner /></div>;
}