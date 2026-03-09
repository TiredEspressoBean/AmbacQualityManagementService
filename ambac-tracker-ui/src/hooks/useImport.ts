import { api } from "@/lib/api/generated";
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

interface ImportParams {
    file: File;
    mode?: ImportMode;
}

/**
 * Generic import hook for any model with the CSVImportMixin.
 *
 * @example
 * ```tsx
 * const { mutate: importParts, isPending } = useImport("Parts", {
 *   onSuccess: (data) => toast.success(`Imported ${data.summary.created} parts`),
 * });
 *
 * importParts({ file: selectedFile, mode: "upsert" });
 * ```
 */
export const useImport = (
    modelName: string,
    options?: {
        invalidateQueries?: string[];
        onSuccess?: (data: ImportResponse) => void;
        onError?: (error: Error) => void;
    }
) => {
    const queryClient = useQueryClient();

    return useMutation<ImportResponse, Error, ImportParams>({
        mutationFn: async ({ file, mode = "upsert" }) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("mode", mode);

            const response = await api.axios.post<ImportResponse>(
                `/api/${modelName}/import/`,
                formData,
                {
                    headers: { "Content-Type": "multipart/form-data" },
                    validateStatus: (status) =>
                        (status >= 200 && status < 300) || status === 207,
                }
            );
            return response.data;
        },
        onSuccess: (data) => {
            const queriesToInvalidate = [
                ...(options?.invalidateQueries ?? []),
                modelName.toLowerCase(),
            ];
            queriesToInvalidate.forEach((key) => {
                queryClient.invalidateQueries({ queryKey: [key] });
            });
            options?.onSuccess?.(data);
        },
        onError: options?.onError,
    });
};
