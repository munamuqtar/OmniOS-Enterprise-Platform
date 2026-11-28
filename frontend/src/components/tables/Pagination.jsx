export default function Pagination({ page, pageSize, count, onPage }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  return (
    <div className="pagination">
      <span className="muted">{count} record{count === 1 ? "" : "s"}</span>
      {pages > 1 && (
        <div className="pager">
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
          <span>Page {page} of {pages}</span>
          <button className="btn btn-ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}