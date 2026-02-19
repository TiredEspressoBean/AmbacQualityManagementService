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
};

const TenantContext = createContext<TenantContextValue | null>(null);

type TenantProviderProps = {
    children: ReactNode;
};

export function TenantProvider({ children }: TenantProviderProps) {
    const { data, isLoading, isError, refetch } = useTenant();

    // Apply tenant branding colors when data loads
    useEffect(() => {
        if (!data?.tenant) {
            resetBrandingColors();
            return;
        }

        // Colors come from settings.branding on backend
        const primaryColor = data.tenant.primary_color;
        const secondaryColor = (data.tenant as { secondary_color?: string | null }).secondary_color;

        if (primaryColor) {
            applyBrandingColors(primaryColor, secondaryColor ?? undefined);
        } else {
            resetBrandingColors();
        }

        // Cleanup on unmount
        return () => resetBrandingColors();
    }, [data?.tenant?.primary_color, (data?.tenant as { secondary_color?: string | null })?.secondary_color]);

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
