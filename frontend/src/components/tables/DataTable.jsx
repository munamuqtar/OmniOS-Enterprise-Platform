import { Spinner } from "../common/Spinner";
import EmptyState from "../common/EmptyState";
import ErrorBanner from "../common/ErrorBanner";
import Pagination from "./Pagination";

/** columns: [{ key, header, render?(row), width? }]. error is a message string. */
export default function DataTable({
  columns, rows, loading, error, onRetry, emptyTitle = "No records found", emptyHint,
  onRowClick, rowKey = "id", pagination,
}) {
  if (error) return <ErrorBanner message={error} onRetry={onRetry} />;
  return (
    <div className="table-card">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>{columns.map((c) => <th key={c.key} style={c.width ? { width: c.width } : undefined}>{c.header}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[rowKey]} className={onRowClick ? "clickable" : ""}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}>
                {columns.map((c) => <td key={c.key}>{c.render ? c.render(row) : row[c.key] ?? "—"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {loading && !rows.length && <Spinner />}
      {!loading && !rows.length && <EmptyState title={emptyTitle} hint={emptyHint} />}
      {pagination && <Pagination {...pagination} />}
    </div>
  );
}