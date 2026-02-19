import { useQuery } from "@tanstack/react-query";
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

export function useAvailablePermissions(options?: { grouped?: boolean; enabled?: boolean }) {
    return useQuery({
        queryKey: ["permissions", options?.grouped],
        queryFn: () => api.api_permissions_retrieve({ grouped: options?.grouped }),
        enabled: options?.enabled ?? true,
    });
}
