import { useMutation, useQueryClient } from "@tanstack/react-query";

type ImportMode = "create" | "update" | "upsert";

interface ImportResult {
    row: number;
    status: "created" | "updated" | "error";
    id?: string;
    errors?: string | Record<string, string> | string[];
    warnings?: string[];
}

interface ImportResponse {
    summary: {
        total: number;
        created: number;
        updated: number;
        errors: number;
    };
    results: ImportResult[];
}

interface UseCsvImportOptions {
    /** Model/endpoint name (e.g., "parts", "orders") */
    modelName: string;
    /** API base URL */
    apiBaseUrl?: string;
    /** Query keys to invalidate after successful import */
    invalidateQueries?: string[];
    /** Callback on success */
    onSuccess?: (data: ImportResponse) => void;
    /** Callback on error */
    onError?: (error: Error) => void;
}

interface ImportMutationVariables {
    file: File;
    mode?: ImportMode;
}

/**
 * Hook for importing data from CSV/Excel files.
 *
 * @example
 * ```tsx
 * const { mutate: importParts, isPending } = useCsvImport({
 *   modelName: "parts",
 *   invalidateQueries: ["parts"],
 *   onSuccess: (data) => {
 *     toast.success(`Imported ${data.summary.created} parts`);
 *   },
 * });
 *
 * // Trigger import
 * importParts({ file: selectedFile, mode: "upsert" });
 * ```
 */
export function useCsvImport({
    modelName,
    apiBaseUrl = "/api",
    invalidateQueries = [],
    onSuccess,
    onError,
}: UseCsvImportOptions) {
    const queryClient = useQueryClient();

    return useMutation<ImportResponse, Error, ImportMutationVariables>({
        mutationFn: async ({ file, mode = "upsert" }) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("mode", mode);

            const response = await fetch(`${apiBaseUrl}/${modelName}/import/`, {
                method: "POST",
                body: formData,
                credentials: "include",
            });

            if (!response.ok && response.status !== 207) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Import failed: ${response.statusText}`);
            }

            return response.json();
        },
        onSuccess: (data) => {
            // Invalidate related queries
            const queriesToInvalidate = [
                ...invalidateQueries,
                modelName,
                `${modelName}List`,
            ];

            queriesToInvalidate.forEach((key) => {
                queryClient.invalidateQueries({ queryKey: [key] });
            });

            onSuccess?.(data);
        },
        onError,
    });
}

/**
 * Hook for downloading import templates.
 *
 * @example
 * ```tsx
 * const { download, isPending } = useImportTemplate({
 *   modelName: "parts",
 * });
 *
 * // Download Excel template
 * download("xlsx");
 * ```
 */
export function useImportTemplate({
    modelName,
    apiBaseUrl = "/api",
}: {
    modelName: string;
    apiBaseUrl?: string;
}) {
    const mutation = useMutation<Blob, Error, "csv" | "xlsx">({
        mutationFn: async (format) => {
            const response = await fetch(
                `${apiBaseUrl}/${modelName}/import-template/?format=${format}`,
                { credentials: "include" }
            );

            if (!response.ok) {
                throw new Error(`Template download failed: ${response.statusText}`);
            }

            return response.blob();
        },
    });

    const download = (format: "csv" | "xlsx" = "xlsx") => {
        mutation.mutate(format, {
            onSuccess: (blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${modelName}_import_template.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            },
        });
    };

    return {
        download,
        isPending: mutation.isPending,
        error: mutation.error,
    };
}
