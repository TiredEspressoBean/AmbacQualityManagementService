import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useDebounce } from "@/hooks/useDebounce";

/**
 * Employee picker options searched on the server, for a `Combobox` (`onSearch`).
 * A first page alone leaves out anyone past it; typing a name finds them.
 */
export function useEmployeeSearch(enabled = true) {
    const [search, setSearch] = useState("");
    const q = useDebounce(search.trim(), 250);
    const { data, isFetching } = useQuery({
        queryKey: ["employee-options", "search", q],
        queryFn: () => api.api_Employees_Options_list({ queries: { offset: 0, ...(q ? { search: q } : {}) } }),
        enabled,
        placeholderData: keepPreviousData,
    });
    const options = (data?.results ?? []).map((e) => ({
        value: String(e.id),
        label: e.full_name?.trim() || e.email || e.username || "Unknown",
    }));
    return { options, onSearch: setSearch, loading: isFetching };
}
