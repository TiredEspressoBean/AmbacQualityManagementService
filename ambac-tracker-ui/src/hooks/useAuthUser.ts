// src/hooks/useAuthUser.ts
import { useQuery, queryOptions } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'

// Group type for both Django groups and tenant groups
export type AuthUserGroup = {
    id: number;
    name: string;
    role_type?: string;
};

// Extended auth user type with fields returned by backend but not in OpenAPI
// spec. The `auth/user/` endpoint's serializer doesn't declare these — they
// get injected at request time by `UserDetailsView.retrieve` (Tracker/viewsets
// /core.py) or come from dj-rest-auth's UserDetailsSerializer. Keep this
// extension in sync with what the backend actually returns. Long-term fix:
// write a tenant-aware UserDetailsSerializer so drf-spectacular emits these
// in the spec.
export type AuthUser = Awaited<ReturnType<typeof api.auth_user_retrieve>> & {
    id?: number;
    // Display
    full_name?: string;
    date_joined?: string;
    parent_company?: { id?: string; name?: string } | null;
    // Django user flags
    is_staff?: boolean;
    is_superuser?: boolean;
    is_active?: boolean;
    // Django permission groups
    groups?: AuthUserGroup[];
    // Tenant-specific groups (multi-tenancy)
    tenant_groups?: AuthUserGroup[];
};

export const authUserOptions = () => queryOptions<AuthUser>({
    queryKey: ['authUser'] as const,
    queryFn: () => api.auth_user_retrieve() as Promise<AuthUser>,
});

export function useAuthUser() {
    return useQuery({
        ...authUserOptions(),
        staleTime: 5 * 60 * 1000, // treat as fresh for 5 minutes
        retry: false,             // don't retry if unauthenticated
    })
}
