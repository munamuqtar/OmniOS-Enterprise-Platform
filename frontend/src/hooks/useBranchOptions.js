import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../services/api/client";
import { useAuth } from "../app/providers/auth-context";

/** Branches the current user may pick: everyone for Super Admin, their own branches otherwise. */
export function useBranchOptions() {
  const { user, isSuperAdmin } = useAuth();
  const all = useQuery({
    queryKey: ["/branches/", "options"], enabled: isSuperAdmin,
    queryFn: async () => unwrap(await api.get("/branches/")).results,
  });
  return isSuperAdmin ? all.data ?? [] : user.branches;
}