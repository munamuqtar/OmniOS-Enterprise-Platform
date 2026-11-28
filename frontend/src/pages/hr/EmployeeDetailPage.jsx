import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../app/providers/auth-context";
import { useDetail } from "../../hooks/useDetail";
import { parseApiError } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import PageHeader from "../../components/common/PageHeader";
import InfoGrid from "../../components/common/InfoGrid";
import StatusBadge from "../../components/common/StatusBadge";
import ErrorBanner from "../../components/common/ErrorBanner";
import { Spinner } from "../../components/common/Spinner";
import EmployeeFormModal from "./EmployeeFormModal";

export default function EmployeeDetailPage() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const employee = useDetail("/employees/", id);
  const [editing, setEditing] = useState(false);

  if (employee.isLoading) return <Spinner />;
  if (employee.error) return <ErrorBanner message={parseApiError(employee.error).message} onRetry={employee.refetch} />;
  const e = employee.data;

  return (
    <>
      <PageHeader title={<>{e.first_name} {e.last_name} <StatusBadge status={e.status} /></>}
                  subtitle={`${e.employee_number}${e.position ? ` · ${e.position}` : ""}`}
                  actions={
                    <>
                      <Link className="btn btn-ghost" to="/hr/employees">Back</Link>
                      {hasRole("hr") && <button className="btn btn-primary" onClick={() => setEditing(true)}>Edit</button>}
                    </>
                  } />
      <section className="card">
        <InfoGrid items={[["Email", e.email], ["Phone", e.phone || null], ["Address", e.address || null],
          ["Department", e.department_name], ["Position", e.position || null], ["Branch", e.branch_name],
          ["Hire date", formatDate(e.hire_date)], ["Login account", e.user_name]]} />
      </section>
      {editing && <EmployeeFormModal employee={e} onClose={() => setEditing(false)} onSaved={() => setEditing(false)} />}
    </>
  );
}