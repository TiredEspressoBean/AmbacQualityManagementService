import { useMutation } from "@tanstack/react-query";

type ExportFormat = "csv" | "xlsx";

interface UseCsvExportOptions {
    /** Model/endpoint name (e.g., "parts", "orders") */
    modelName: string;
    /** API base URL */
    apiBaseUrl?: string;
    /** Fields to export (if not all) */
    fields?: string[];
    /** Custom filename (without extension) */
    filename?: string;
    /** Callback on success */
    onSuccess?: () => void;
    /** Callback on error */
    onError?: (error: Error) => void;
}

interface ExportMutationVariables {
    format?: ExportFormat;
    queryParams?: Record<string, string | number | boolean | undefined>;
    fields?: string[];
    filename?: string;
}

/**
 * Hook for exporting data to CSV/Excel files.
 *
 * @example
 * ```tsx
 * const { mutate: exportParts, isPending } = useCsvExport({
 *   modelName: "parts",
 *   onSuccess: () => toast.success("Export complete"),
 * });
 *
 * // Export with current filters
 * exportParts({
 *   format: "xlsx",
 *   queryParams: { part_status: "IN_PROGRESS" },
 * });
 * ```
 */
export function useCsvExport({
    modelName,
    apiBaseUrl = "/api",
    fields: defaultFields,
    filename: defaultFilename,
    onSuccess,
    onError,
}: UseCsvExportOptions) {
    return useMutation<void, Error, ExportMutationVariables>({
        mutationFn: async ({
            format = "xlsx",
            queryParams,
            fields = defaultFields,
            filename = defaultFilename,
        }) => {
            const url = new URL(`${apiBaseUrl}/${modelName}/export/`, window.location.origin);
            url.searchParams.set("format", format);

            if (fields && fields.length > 0) {
                url.searchParams.set("fields", fields.join(","));
            }

            if (filename) {
                url.searchParams.set("filename", filename);
            }

            // Add query params (filters, search, ordering)
            if (queryParams) {
                Object.entries(queryParams).forEach(([key, value]) => {
                    if (value !== undefined && value !== null && value !== "") {
                        url.searchParams.set(key, String(value));
                    }
                });
            }

            const response = await fetch(url.toString(), { credentials: "include" });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Get filename from Content-Disposition header if available
            const contentDisposition = response.headers.get("Content-Disposition");
            let downloadFilename = `${filename || modelName}_export.${format}`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    downloadFilename = filenameMatch[1];
                }
            }

            const blob = await response.blob();
            downloadBlob(blob, downloadFilename);
        },
        onSuccess,
        onError,
    });
}

/**
 * Simple hook for downloading filtered data export.
 *
 * Returns a download function that can be called with format and filters.
 *
 * @example
 * ```tsx
 * const { download, isPending } = useDataExport("parts");
 *
 * <Button onClick={() => download("xlsx", { part_status: "IN_PROGRESS" })}>
 *   Export Active Parts
 * </Button>
 * ```
 */
export function useDataExport(
    modelName: string,
    apiBaseUrl: string = "/api"
) {
    const mutation = useMutation<
        void,
        Error,
        {
            format: ExportFormat;
            queryParams?: Record<string, string | number | boolean | undefined>;
        }
    >({
        mutationFn: async ({ format, queryParams }) => {
            const url = new URL(`${apiBaseUrl}/${modelName}/export/`, window.location.origin);
            url.searchParams.set("format", format);

            if (queryParams) {
                Object.entries(queryParams).forEach(([key, value]) => {
                    if (value !== undefined && value !== null && value !== "") {
                        url.searchParams.set(key, String(value));
                    }
                });
            }

            const response = await fetch(url.toString(), { credentials: "include" });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            downloadBlob(blob, `${modelName}_export.${format}`);
        },
    });

    const download = (
        format: ExportFormat = "xlsx",
        queryParams?: Record<string, string | number | boolean | undefined>
    ) => {
        mutation.mutate({ format, queryParams });
    };

    return {
        download,
        isPending: mutation.isPending,
        error: mutation.error,
    };
}

// Utility function to trigger file download
function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
