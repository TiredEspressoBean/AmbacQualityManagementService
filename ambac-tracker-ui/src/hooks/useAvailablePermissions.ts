import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type Permission = {
    codename: string;
    name: string;
    category?: string;
    content_type?: string;
};

export type PermissionGroup = {
    category: string;
    permissions: Permission[];
};

export const availablePermissionsOptions = (grouped?: boolean) => queryOptions({
    queryKey: ["permissions", grouped] as const,
    queryFn: () => api.api_permissions_retrieve({ queries: { grouped } }),
});

export function useAvailablePermissions(options?: { grouped?: boolean; enabled?: boolean }) {
    return useQuery({
        ...availablePermissionsOptions(options?.grouped),
        enabled: options?.enabled ?? true,
    });
}
