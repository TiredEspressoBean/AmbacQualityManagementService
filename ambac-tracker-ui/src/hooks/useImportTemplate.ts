import { api } from "@/lib/api/generated";
import { useMutation } from "@tanstack/react-query";

type TemplateFormat = "csv" | "xlsx";

/**
 * Generic import template hook for any model with the CSVImportMixin.
 *
 * @example
 * ```tsx
 * const { mutate: downloadTemplate, isPending } = useImportTemplate("Parts");
 *
 * downloadTemplate("xlsx");
 * ```
 */
export const useImportTemplate = (modelName: string) => {
    return useMutation<Blob, Error, TemplateFormat>({
        mutationFn: async (format) => {
            const response = await api.axios.get(
                `/api/${modelName}/import-template/${format}/`,
                { responseType: "blob" }
            );
            return response.data;
        },
        onSuccess: (blob, format) => {
            const filename = `${modelName.toLowerCase()}_import_template.${format}`;
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
