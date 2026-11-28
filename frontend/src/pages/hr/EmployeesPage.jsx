import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/providers/auth-context";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { useDepartments } from "../../hooks/useDepartments";
import { usePaginatedList } from "../../hooks/usePaginatedList";
import { parseApiError } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import DataTable from "../../components/tables/DataTable";
import SearchBox, { FilterSelect } from "../../components/forms/SearchBox";
import DepartmentsDialog from "./DepartmentsDialog";
import EmployeeFormModal from "./EmployeeFormModal";
import { EMPLOYEE_STATUSES } from "../../utils/constants";

export default function EmployeesPage() {
  const { user, hasRole } = useAuth();
  const canWrite = hasRole("hr");
  const onlyEmployee = user.roles.length === 1 && user.roles[0] === "employee";
  const list = usePaginatedList("/employees/");
  const branches = useBranchOptions();
  const departments = useDepartments();
  const navigate = useNavigate();
  const [dialog, setDialog] = useState(null);           // "new" | "departments"

  const columns = [
    { key: "employee_number", header: "Number" },
    { key: "name", header: "Name", render: (r) => `${r.first_name} ${r.last_name}` },
    { key: "email", header: "Email" },
    { key: "department_name", header: "Department" },
    { key: "position", header: "Position" },
    { key: "branch_name", header: "Branch" },
    { key: "hire_date", header: "Hired", render: (r) => formatDate(r.hire_date) },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
  ];

  return (
    <>
      <PageHeader title={onlyEmployee ? "My profile" : "Employee directory"}
                  subtitle={onlyEmployee ? "Your employee record" : "People across your branches"}
                  actions={canWrite && (
                    <>
                      <button className="btn btn-ghost" onClick={() => setDialog("departments")}>Departments</button>
                      <button className="btn btn-primary" onClick={() => setDialog("new")}>New employee</button>
                    </>
                  )} />
      {!onlyEmployee && (
        <div className="filters">
          <SearchBox value={list.searchInput} onChange={list.setSearchInput} placeholder="Search name, number, email, position…" />
          <FilterSelect label="Department" allLabel="All departments" value={list.filters.department ?? ""}
                        onChange={(v) => list.setFilter("department", v)}
                        options={departments.map((d) => ({ value: d.id, label: d.name }))} />
          <FilterSelect label="Status" allLabel="All statuses" value={list.filters.status ?? ""}
                        onChange={(v) => list.setFilter("status", v)} options={EMPLOYEE_STATUSES} />
          {branches.length > 1 && (
            <FilterSelect label="Branch" allLabel="All branches" value={list.filters.branch ?? ""}
                          onChange={(v) => list.setFilter("branch", v)}
                          options={branches.map((b) => ({ value: b.id, label: b.name }))} />
          )}
        </div>
      )}
      <DataTable columns={columns} rows={list.rows} loading={list.isLoading}
                 error={list.error && parseApiError(list.error).message} onRetry={list.refetch}
                 onRowClick={(r) => navigate(`/hr/employees/${r.id}`)}
                 emptyTitle="No employees found" emptyHint={onlyEmployee ? "Your employee record has not been created yet. Ask HR." : "Add your first employee."}
                 pagination={{ page: list.page, pageSize: list.pageSize, count: list.count, onPage: list.setPage }} />
      {dialog === "new" && <EmployeeFormModal onClose={() => setDialog(null)}
                                              onSaved={(e) => { setDialog(null); navigate(`/hr/employees/${e.id}`); }} />}
      {dialog === "departments" && <DepartmentsDialog onClose={() => setDialog(null)} />}
    </>
  );
}