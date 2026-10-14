/**
 * Signing one block inside a substep, and undoing it before the substep is submitted.
 *
 * A `signature` attestation block is signed where it sits: the operator draws and
 * re-enters their own password, and the server records it against
 * (execution, substep, node) with the block's label as the meaning.
 *
 * Until the substep is submitted the signature is provisional, so it can be undone —
 * by whoever signed it, always; by a supervisor holding `clear_gate_signature` when
 * the signer has gone off shift. Once submitted it stands, and only QA's void on the
 * completion retracts it.
 */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

export type GateSignature = {
    id: string;
    node_id: string;
    completed_by: number | null;
    completed_by_name?: string | null;
    completed_at?: string | null;
    signature_meaning?: string | null;
    verification_method?: string | null;
};

type Scope = { stepExecutionId?: string | null; batchExecutionId?: string | null; substepId?: string | null };

const key = (s: Scope) =>
    ["gate-signatures", s.substepId ?? "", s.stepExecutionId ?? "", s.batchExecutionId ?? ""] as const;

export const gateSignaturesOptions = (s: Scope) =>
    queryOptions({
        queryKey: key(s),
        queryFn: () =>
            api.api_SubstepGateCompletions_list({
                queries: {
                    substep: String(s.substepId),
                    ...(s.stepExecutionId ? { step_execution: String(s.stepExecutionId) } : {}),
                    ...(s.batchExecutionId ? { batch_execution: String(s.batchExecutionId) } : {}),
                },
            }) as Promise<{ results?: GateSignature[] } | GateSignature[]>,
        enabled: !!s.substepId && !!(s.stepExecutionId || s.batchExecutionId),
        select: (d): GateSignature[] => (Array.isArray(d) ? d : d.results ?? []),
    });

export function useGateSignatures(s: Scope) {
    return useQuery(gateSignaturesOptions(s));
}

export function useSignGate(s: Scope) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { nodeId: string; signature_data: string; password: string }) =>
            api.api_SubstepGateCompletions_create(
                {
                    substep: String(s.substepId),
                    node_id: vars.nodeId,
                    signature_data: vars.signature_data,
                    ...(s.stepExecutionId ? { step_execution: String(s.stepExecutionId) } : {}),
                    ...(s.batchExecutionId ? { batch_execution: String(s.batchExecutionId) } : {}),
                    password: vars.password,
                } as Parameters<typeof api.api_SubstepGateCompletions_create>[0],
                { headers: csrf() },
            ),
        // The dialog shows the server's reason (wrong password, already submitted).
        meta: { suppressGlobalError: true },
        onSuccess: () => void qc.invalidateQueries({ queryKey: key(s) }),
    });
}

export function useClearGateSignature(s: Scope) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id: string) =>
            api.api_SubstepGateCompletions_destroy(undefined, { params: { id }, headers: csrf() }),
        meta: { suppressGlobalError: true },
        onSuccess: () => void qc.invalidateQueries({ queryKey: key(s) }),
    });
}
