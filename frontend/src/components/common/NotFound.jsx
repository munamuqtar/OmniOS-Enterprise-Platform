import { Link } from "react-router-dom";
import EmptyState from "./EmptyState";

export default function NotFound() {
  return (
    <EmptyState title="Page not found" hint="This page does not exist.">
      <Link className="btn btn-primary" to="/dashboard">Back to dashboard</Link>
    </EmptyState>
  );
}