/**
 * Default branding configuration for white-label deployment.
 * These values are used when tenant-specific branding is not configured.
 */
export const DEFAULT_BRANDING = {
    appName: "uqmes",
    appFullName: "Unified Quality MES",
    tagline: "Quality Manufacturing Execution System",
} as const;

/**
 * Get the application name to display in the UI.
 * Falls back to default if tenant name is not configured.
 */
export function getAppName(tenantName?: string | null): string {
    return tenantName || DEFAULT_BRANDING.appName;
}

/**
 * Get the application tagline to display in the UI.
 */
export function getAppTagline(): string {
    return DEFAULT_BRANDING.tagline;
}
