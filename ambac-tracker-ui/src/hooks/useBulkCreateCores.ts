import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export type BulkCoreRow = {
    core_number: string;
    core_type: string;
    received_date: string;
    source_type: string;
    condition_grade: string;
    serial_number?: string;
    customer?: string | null;
    source_reference?: string;
    condition_notes?: string;
    core_credit_value?: string | null;
};

type BulkCreateCoresVars = {
    cores: BulkCoreRow[];
};

export const useBulkCreateCores = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: BulkCreateCoresVars) =>
            api.api_Cores_bulk_create_create(
                { cores: vars.cores as never },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "cores" || q.queryKey[0] === "core",
            });
        },
    });
};