import { Link } from "react-router-dom";
import EmptyState from "./EmptyState";

export default function PermissionDenied() {
  return (
    <EmptyState title="Access denied" hint="You do not have access to this page.">
      <Link className="btn btn-primary" to="/dashboard">Back to dashboard</Link>
    </EmptyState>
  );
}