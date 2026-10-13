// src/hooks/useAuthUser.ts
import { useQuery, queryOptions } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'

// Tenant-group shape on the auth payload — exactly what the backend returns:
// `[{id: str(TenantGroup UUID), name}]` (TenantAwareUserDetailsSerializer.get_groups).
// No other fields exist; don't add phantoms here.
export type AuthUserGroup = {
    id: string | number;
    name: string;
};

// Extended auth user type with fields returned by backend but not in OpenAPI
// spec. The `auth/user/` endpoint's serializer doesn't declare these — they
// get injected at request time by `UserDetailsView.retrieve` (Tracker/viewsets
// /core.py) or come from dj-rest-auth's UserDetailsSerializer. Keep this
// extension in sync with what the backend actually returns. Long-term fix:
// write a tenant-aware UserDetailsSerializer so drf-spectacular emits these
// in the spec.
// NOTE: there is deliberately no `id` here. The endpoint returns the user as
// `pk` (see TenantAwareUserDetails). An optional `id?: number` used to sit in
// this block, which made `me.id` compile everywhere while always evaluating to
// undefined — the DWI signature nodes recorded `user_id: null` for every
// signature taken in the player because of it. Use `me.pk`.
export type AuthUser = Awaited<ReturnType<typeof api.auth_user_retrieve>> & {
    // full_name / date_joined / parent_company are on the payload now
    // (TenantAwareUserDetailsSerializer); they used to be optional phantoms here, so
    // the profile page fell back to the username, "—" and "No company assigned".
    // Tenant-scoped groups (UserRole memberships in the user's tenant), NOT
    // Django auth groups — TenantAwareUserDetailsSerializer.get_groups returns
    // TenantGroup rows filtered to the user's tenant. There is no separate
    // `tenant_groups` field on any user endpoint; this is the only one.
    groups?: AuthUserGroup[];
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
