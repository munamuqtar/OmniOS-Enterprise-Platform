import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../services/api/client";

/** Loads one record (or a sub-resource such as "history/"). Disabled while id is undefined. */
export function useDetail(endpoint, id, suffix = "") {
  return useQuery({
    queryKey: [endpoint, "detail", id, suffix],
    enabled: id != null,
    queryFn: async () => unwrap(await api.get(`${endpoint}${id}/${suffix}`)),
  });
}