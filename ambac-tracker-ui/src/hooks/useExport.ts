import { api } from "@/lib/api/generated";
import { useMutation } from "@tanstack/react-query";

type ExportFormat = "csv" | "xlsx";

interface ExportParams {
    format: ExportFormat;
    fields?: string;
    filename?: string;
    /** Additional query params (filters, etc.) */
    queries?: Record<string, string | number | boolean | string[] | undefined>;
}

/**
 * Generic export hook for any model with the DataExportMixin.
 *
 * @example
 * ```tsx
 * const { mutate: exportParts, isPending } = useExport("Parts");
 *
 * exportParts({
 *   format: "xlsx",
 *   queries: { status__in: ["IN_PROGRESS", "COMPLETE"] },
 * });
 * ```
 */
export const useExport = (modelName: string) => {
    return useMutation<Blob, Error, ExportParams>({
        mutationFn: async ({ format, fields, filename, queries }) => {
            const response = await api.axios.get(
                `/api/${modelName}/export/${format}/`,
                {
                    params: { fields, filename, ...queries },
                    responseType: "blob",
                }
            );
            return response.data;
        },
        onSuccess: (blob, variables) => {
            const filename = variables.filename
                ?? `${modelName.toLowerCase()}_export.${variables.format}`;
            downloadBlob(blob, filename);
        },
    });
};

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
