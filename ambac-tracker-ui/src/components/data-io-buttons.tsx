import { useQueryClient } from "@tanstack/react-query";
import { DataExportMenu } from "@/components/data-export-menu";
import { DataImportDialog } from "@/components/data-import-dialog";
import { hasEndpoint } from "@/lib/api/endpoint-fn";
import { matchKey } from "@/lib/query-filters";

interface DataIOButtonsProps {
    /** API route under /api/, e.g. "JobRoles" or "notifications/external-contacts". */
    endpoint: string;
    /** Dialog title; defaults to one derived from the endpoint. */
    displayName?: string;
    /** Query key prefixes to invalidate after an import lands (the page's list query). */
    invalidateKeys: readonly (readonly unknown[])[];
    /** Current list filters/search, passed through to the export. */
    queryParams?: Record<string, string | number | boolean | undefined>;
    /** False hides Import (a read-only surface); Export still shows. */
    allowImport?: boolean;
}

/**
 * Import dialog + Export menu for a custom list page, the same pair ModelEditorPage
 * renders in its toolbar, and gated the same way: each button appears only when the
 * generated client has that endpoint, so a model without import never offers a dialog
 * whose every call 404s.
 */
export function DataIOButtons({
    endpoint, displayName, invalidateKeys, queryParams, allowImport = true,
}: DataIOButtonsProps) {
    const queryClient = useQueryClient();
    const canImport = allowImport && hasEndpoint(endpoint, "import_create");
    const canExport = hasEndpoint(endpoint, "export_retrieve");
    if (!canImport && !canExport) return null;
    return (
        <>
            {canImport && (
                <DataImportDialog
                    modelName={endpoint}
                    {...(displayName ? { displayName } : {})}
                    onImportComplete={() => {
                        for (const key of invalidateKeys) {
                            queryClient.invalidateQueries(matchKey(key));
                        }
                    }}
                />
            )}
            {canExport && (
                <DataExportMenu
                    modelName={endpoint}
                    showTemplateOption={hasEndpoint(endpoint, "import_template_retrieve")}
                    {...(queryParams ? { queryParams } : {})}
                />
            )}
        </>
    );
}
