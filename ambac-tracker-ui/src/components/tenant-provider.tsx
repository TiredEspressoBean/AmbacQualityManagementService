import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useTenant, type DeploymentInfo } from "@/hooks/useTenant";
import type { TenantInfo } from "@/lib/api/generated";
import { applyBrandingColors, resetBrandingColors } from "@/lib/color-utils";

type TenantContextValue = {
    tenant: TenantInfo | null;
    deployment: DeploymentInfo | null;
    features: Record<string, boolean>;
    limits: Record<string, number>;
    isLoading: boolean;
    isError: boolean;
    refetch: () => void;
    // Convenience flags
    isSaas: boolean;
    isDedicated: boolean;
    isDemo: boolean;
    // Change-control posture. SIMPLIFIED single-click flows vs
    // REGULATED signature-gated flows. Defaults to SIMPLIFIED when
    // tenant info hasn't loaded so UI affordances fail open to the
    // simpler (but still backend-guarded) experience.
    changeControlMode: "SIMPLIFIED" | "REGULATED";
    isRegulated: boolean;
};

const TenantContext = createContext<TenantContextValue | null>(null);

type TenantProviderProps = {
    children: ReactNode;
};

export function TenantProvider({ children }: TenantProviderProps) {
    const { data, isLoading, isError, refetch } = useTenant();

    // Apply tenant branding colors when data loads
    const tenant = data?.tenant;
    const primaryColor = tenant?.primary_color ?? null;
    const tenantExt = tenant as
        | {
              secondary_color?: string | null;
              tint_strength?: number | string | null;
          }
        | undefined;
    const secondaryColor = tenantExt?.secondary_color ?? null;
    const tintStrengthRaw = tenantExt?.tint_strength ?? null;
    const tintStrength = (() => {
        if (tintStrengthRaw === null || tintStrengthRaw === undefined) return undefined;
        const n = typeof tintStrengthRaw === "number" ? tintStrengthRaw : parseFloat(tintStrengthRaw);
        return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : undefined;
    })();
    useEffect(() => {
        if (!tenant) {
            resetBrandingColors();
            return;
        }

        // Colors come from settings.branding on backend
        if (primaryColor) {
            applyBrandingColors(primaryColor, secondaryColor ?? undefined, tintStrength);
        } else {
            resetBrandingColors();
        }

        // Cleanup on unmount
        return () => resetBrandingColors();
    }, [tenant, primaryColor, secondaryColor, tintStrength]);

    const value: TenantContextValue = {
        tenant: data?.tenant ?? null,
        deployment: data?.deployment ?? null,
        features: (data?.features as Record<string, boolean>) ?? {},
        limits: (data?.limits as Record<string, number>) ?? {},
        isLoading,
        isError,
        refetch,
        isSaas: data?.deployment?.is_saas ?? false,
        isDedicated: data?.deployment?.is_dedicated ?? false,
        isDemo: data?.tenant?.is_demo ?? false,
        changeControlMode:
            (data?.tenant as { change_control_mode?: string | null } | null | undefined)
                ?.change_control_mode === "REGULATED"
                ? "REGULATED"
                : "SIMPLIFIED",
        isRegulated:
            (data?.tenant as { change_control_mode?: string | null } | null | undefined)
                ?.change_control_mode === "REGULATED",
    };

    return (
        <TenantContext.Provider value={value}>
            {children}
        </TenantContext.Provider>
    );
}

export function useTenantContext(): TenantContextValue {
    const context = useContext(TenantContext);
    if (!context) {
        throw new Error("useTenantContext must be used within a TenantProvider");
    }
    return context;
}
