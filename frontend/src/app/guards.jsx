import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./providers/auth-context";
import { FullPageSpinner } from "../components/common/Spinner";
import PermissionDenied from "../components/common/PermissionDenied";

export function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/** roles: null = any signed-in user, [] = Super Admin only, ["hr"] = HR (and Super Admin). */
export function Guard({ roles, children }) {
  const { hasRole } = useAuth();
  if (roles && !hasRole(...roles)) return <PermissionDenied />;
  return children;
}