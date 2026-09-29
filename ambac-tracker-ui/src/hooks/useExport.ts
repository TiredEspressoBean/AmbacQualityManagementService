import { api } from "@/lib/api/generated";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { blobErrorMessage, downloadBlob } from "@/lib/download";

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
        // Without this a refused download (too many rows, no permission) did nothing.
        onError: async (error) => {
            toast.error(await blobErrorMessage(error, "Export failed."));
        },
    });
};
