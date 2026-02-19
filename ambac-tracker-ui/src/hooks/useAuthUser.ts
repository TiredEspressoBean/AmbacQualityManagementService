// src/hooks/useAuthUser.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'

// Group type for both Django groups and tenant groups
export type AuthUserGroup = {
    id: number;
    name: string;
    role_type?: string;
};

// Extended auth user type with fields returned by backend but not in OpenAPI spec
export type AuthUser = Awaited<ReturnType<typeof api.auth_user_retrieve>> & {
    id?: number;
    // Django user flags
    is_staff?: boolean;
    is_superuser?: boolean;
    is_active?: boolean;
    // Django permission groups
    groups?: AuthUserGroup[];
    // Tenant-specific groups (multi-tenancy)
    tenant_groups?: AuthUserGroup[];
};

export function useAuthUser() {
    return useQuery({
        queryKey: ['authUser'],
        queryFn: () => api.auth_user_retrieve() as Promise<AuthUser>,
        staleTime: 5 * 60 * 1000, // treat as fresh for 5 minutes
        retry: false,             // don't retry if unauthenticated
    })
}
