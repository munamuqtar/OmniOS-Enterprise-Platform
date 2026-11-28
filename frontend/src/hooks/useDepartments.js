import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../services/api/client";

export function useDepartments() {
  const q = useQuery({
    queryKey: ["/departments/", "all"],
    queryFn: async () => unwrap(await api.get("/departments/")).results,
  });
  return q.data ?? [];
}