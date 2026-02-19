import { useQuery } from "@tanstack/react-query";

export type UserTenant = {
    id: string;
    name: string;
    slug: string;
    logo_url: string | null;
    tier: string;
    is_current: boolean;
};

/**
 * Fetch all tenants the current user has access to.
 * Used for the tenant switcher in the sidebar.
 */
export function useUserTenants() {
    return useQuery({
        queryKey: ["user", "tenants"],
        queryFn: async (): Promise<UserTenant[]> => {
            const response = await fetch("/api/user/tenants/", {
                credentials: "include",
            });
            if (!response.ok) {
                throw new Error("Failed to fetch user tenants");
            }
            return response.json();
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
