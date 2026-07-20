import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type JobRolesListQueries = NonNullable<operations["api_JobRoles_list"]["parameters"]["query"]>;
type JobRolesListResponse = components["schemas"]["PaginatedJobRoleList"];

export const jobRolesOptions = (queries?: JobRolesListQueries) => queryOptions({
    queryKey: ["job-roles", queries] as const,
    queryFn: () =>
        api.api_JobRoles_list((queries ? { queries } : undefined) as never) as Promise<JobRolesListResponse>,
});

export function useJobRoles(queries?: JobRolesListQueries) {
    return useQuery({ ...jobRolesOptions(queries) });
}
