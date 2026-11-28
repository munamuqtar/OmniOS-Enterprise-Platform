import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../services/api/client";

export const PAGE_SIZE = 20;

export function usePaginatedList(endpoint, initialFilters = {}) {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(initialFilters);

  useEffect(() => {                                   // wait 300 ms after typing stops
    const t = setTimeout(() => { setSearch(searchInput.trim()); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const params = useMemo(() => {
    const p = { page };
    if (search) p.search = search;
    Object.entries(filters).forEach(([k, v]) => { if (v !== "" && v != null) p[k] = v; });
    return p;
  }, [page, search, filters]);

  const query = useQuery({
    queryKey: [endpoint, params],
    queryFn: async () => unwrap(await api.get(endpoint, { params })),
    placeholderData: keepPreviousData,
  });

  const setFilter = (key, value) => { setFilters((f) => ({ ...f, [key]: value })); setPage(1); };

  return {
    rows: query.data?.results ?? [], count: query.data?.count ?? 0,
    page, setPage, pageSize: PAGE_SIZE,
    searchInput, setSearchInput, filters, setFilter,
    isLoading: query.isLoading, isFetching: query.isFetching, error: query.error, refetch: query.refetch,
  };
}