import { useState } from "react";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDateTime, titleCase } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import Modal from "../../components/modals/Modal";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";

const MODULES = ["organizations", "branches", "accounts", "hr", "recruitment", "crm", "sales", "projects", "timesheets", "finance", "auth"]
  .map((v) => ({ value: v, label: titleCase(v) }));
const ACTIONS = ["create", "update", "status_change", "delete", "login"].map((v) => ({ value: v, label: titleCase(v) }));
const show = (v) => (v === null || v === undefined || v === "" ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));

function DiffModal({ log, onClose }) {
  const keys = [...new Set([...Object.keys(log.old_values ?? {}), ...Object.keys(log.new_values ?? {})])];
  return (
    <Modal title={`${titleCase(log.action)} · ${log.record_repr}`} onClose={onClose}
           footer={<button className="btn btn-ghost" onClick={onClose}>Close</button>}>
      <p className="muted">{log.user_name ?? "System"} · {formatDateTime(log.created_at)}{log.ip_address && ` · ${log.ip_address}`}</p>
      {keys.length ? (
        <div className="table-scroll">
          <table className="diff">
            <thead><tr><th>Field</th><th>Before</th><th>After</th></tr></thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k}><td>{titleCase(k)}</td><td>{show(log.old_values?.[k])}</td><td>{show(log.new_values?.[k])}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p>No field values were recorded for this entry.</p>}
    </Modal>
  );
}

export default function AuditLogsPage() {
  const list = usePaginatedList("/audit-logs/");
  const [selected, setSelected] = useState(null);
  const columns = [
    { key: "created_at", header: "When", render: (r) => formatDateTime(r.created_at) },
    { key: "user_name", header: "User", render: (r) => r.user_name ?? "System" },
    { key: "action", header: "Action", render: (r) => titleCase(r.action) },
    { key: "module", header: "Module", render: (r) => titleCase(r.module) },
    { key: "record_repr", header: "Record" },
    { key: "ip_address", header: "IP" },
  ];
  return (
    <>
      <PageHeader title="Audit logs" subtitle="Who changed what, and when. Entries cannot be edited." />
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search record or user…" />
        <FilterSelect label="Module" allLabel="All modules" value={list.filters.module ?? ""}
                      onChange={(v) => list.setFilter("module", v)} options={MODULES} />
        <FilterSelect label="Action" allLabel="All actions" value={list.filters.action ?? ""}
                      onChange={(v) => list.setFilter("action", v)} options={ACTIONS} />
        <input className="input" type="date" aria-label="From date" value={list.filters.date_from ?? ""}
               onChange={(e) => list.setFilter("date_from", e.target.value)} />
        <input className="input" type="date" aria-label="To date" value={list.filters.date_to ?? ""}
               onChange={(e) => list.setFilter("date_to", e.target.value)} />
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => setSelected(r)} emptyTitle="No audit entries" emptyHint="Changes you are allowed to see will appear here."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {selected && <DiffModal log={selected} onClose={() => setSelected(null)} />}
    </>
  );
}