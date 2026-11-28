import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import DataTable from "../../components/tables/DataTable";
import SearchBox from "../../components/forms/SearchBox";
import CandidateFormModal from "./CandidateFormModal";

export default function CandidatesTab() {
  const navigate = useNavigate();
  const list = usePaginatedList("/candidates/");
  const [creating, setCreating] = useState(false);
  const columns = [
    { key: "name", header: "Candidate", render: (r) => `${r.first_name} ${r.last_name}` },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    { key: "source", header: "Source" },
    { key: "branch_name", header: "Branch" },
    { key: "created_at", header: "Registered", render: (r) => formatDate(r.created_at) },
  ];
  return (
    <>
      <div className="filters">
        <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name, email, phone…" />
        <button className="btn btn-primary" onClick={() => setCreating(true)}>New candidate</button>
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/hr/recruitment/candidates/${r.id}`)}
                 emptyTitle="No candidates yet" emptyHint="Register your first candidate."
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {creating && <CandidateFormModal onClose={() => setCreating(false)}
                                       onSaved={(c) => { setCreating(false); navigate(`/hr/recruitment/candidates/${c.id}`); }} />}
    </>
  );
}