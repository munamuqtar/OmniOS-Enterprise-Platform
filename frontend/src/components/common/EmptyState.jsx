export default function EmptyState({ title, hint, children }) {
  return (
    <div className="state empty">
      <strong>{title}</strong>
      {hint && <span>{hint}</span>}
      {children}
    </div>
  );
}