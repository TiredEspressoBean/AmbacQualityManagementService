import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export type BulkCoreRow = {
    /** Optional: a blank is auto-numbered CORE-YYYY-#### server-side, which is the
     *  point on a batch — nobody should hand-type forty unique numbers. Send it only
     *  when the shop has its own tagging scheme. */
    core_number?: string;
    core_type: string;
    received_date: string;
    source_type: string;
    condition_grade: string;
    serial_number?: string;
    customer?: string | null;
    source_reference?: string;
    condition_notes?: string;
    core_credit_value?: string | null;
    /** Whether each unit goes back to its customer or they get one from stock.
     *  Per ROW, not per paste: a batch routinely mixes arrangements, and one mode for
     *  forty cores is how a repair-and-return unit gets pooled. */
    fulfilment_mode?: "EXCHANGE" | "REPAIR_RETURN";
};

type BulkCreateCoresVars = {
    cores: BulkCoreRow[];
};

export const useBulkCreateCores = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: BulkCreateCoresVars) =>
            api.api_Cores_bulk_create_create(
                { cores: vars.cores },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "cores" || q.queryKey[0] === "core",
            });
        },
    });
};