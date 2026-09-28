import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";
import { getCookie } from "@/lib/utils";

/** Bulk core receipt and assigning identity — Documents/CORE_AS_PART_DESIGN.md §6.
 *  Cores that arrive counted but unidentified are received as a lot of the core type;
 *  each unit is given its identity (core number, part, core role) when the shop
 *  chooses, and from then on is an ordinary exchange core. */

export type CoreLot = components["schemas"]["CoreLot"];
export type CoreLotReceive = components["schemas"]["CoreLotReceiveRequest"];
export type CoreAssignIdentity = components["schemas"]["CoreAssignIdentityRequest"];

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

export const useCoreLots = () =>
    useQuery({
        queryKey: ["core-lots"],
        queryFn: () => api.api_Cores_lots_list() as Promise<CoreLot[]>,
    });

/** Lots, cores, and everything that counts the bank (the RECOVER lane, sourcing). */
const invalidateBank = (qc: ReturnType<typeof useQueryClient>) =>
    qc.invalidateQueries({
        predicate: (q) => ["core-lots", "cores", "core"].includes(String(q.queryKey[0]))
            || (q.queryKey[0] === "schedule" && q.queryKey[1] === "requirements"),
    });

export const useReceiveCoreLot = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body: CoreLotReceive) =>
            api.api_Cores_receive_lot_create(body, { headers: csrf() }),
        onSuccess: () => invalidateBank(qc),
    });
};

export const useAssignCoreIdentity = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body: CoreAssignIdentity) =>
            api.api_Cores_assign_identity_create(body, { headers: csrf() }),
        onSuccess: () => invalidateBank(qc),
    });
};
