/**
 * Scanning. A handheld scanner is a keyboard: it types the code and presses Enter, so
 * every scan field is an ordinary input that acts on Enter. What the code *is* — a lot,
 * a serial, a work order, a location label (`LOC:…`) or one of our label QR URLs — is
 * decided in one place on the server (`/api/scan/`); this is its client.
 */
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type ScanResult = Schema<"ScanResult">;

export const LOCATION_PREFIX = "LOC:";

/** What ``code`` names, or null when nothing matches. Other failures throw. */
export async function resolveScan(code: string): Promise<ScanResult | null> {
    const q = code.trim();
    if (!q) return null;
    try {
        return (await api.api_scan_list({ queries: { code: q } })) as unknown as ScanResult;
    } catch (err) {
        if ((err as { response?: { status?: number } })?.response?.status === 404) return null;
        throw err;
    }
}

/** A location as typed or scanned: strips a label's `LOC:` prefix. */
export function locationFromScan(code: string): string {
    const q = code.trim();
    return q.toUpperCase().startsWith(LOCATION_PREFIX) ? q.slice(LOCATION_PREFIX.length).trim() : q;
}

export const locationPath = (name: string) => `/production/locations/${encodeURIComponent(name)}`;
