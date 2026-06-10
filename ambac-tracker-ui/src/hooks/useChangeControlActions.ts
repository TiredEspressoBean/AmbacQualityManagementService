import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Lifecycle action mutations for PCR / PCO / PCN.
 *
 * All endpoints are POST `/api/<artifact>/{id}/<action>/`. Bodies vary:
 *   - PCR approve/cancel/reject — narrative reason or nothing
 *   - PCO author/implement/cancel — structured payloads
 *   - PCN release/close — closure_evidence on close
 *
 * Raw fetch (not Zodios) because most of these flip status mid-call;
 * Zodios's auto-parsed response schemas are unreliable across the
 * transition. We invalidate the relevant query keys on success so the
 * detail page reflects new status without a manual reload.
 */

type Artifact = "process-change-requests" | "process-change-orders" | "process-change-notices";

/**
 * Conflict surfaced by the PCR approve endpoint when the draft can't be
 * lifted onto the current baseline (another PCR approved an overlapping
 * change while this PCR was open). Thrown as a typed error so the UI
 * can render the structured conflict list instead of a string.
 */
export type RebaseConflict = {
    detail: string;
    baseline_version_id: string;
    current_approved_id: string;
    conflicts: Array<{
        step_identity_id: string;
        step_name: string;
        field: string;
        intent_value: unknown;
        approved_value: unknown;
    }>;
};

export class PcrRebaseConflictError extends Error {
    readonly conflict: RebaseConflict;
    constructor(conflict: RebaseConflict) {
        super(conflict.detail);
        this.name = "PcrRebaseConflictError";
        this.conflict = conflict;
    }
}

async function post(artifact: Artifact, id: string, action: string, body?: unknown) {
    const r = await fetch(`/api/${artifact}/${id}/${action}/`, {
        method: "POST",
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") ?? "",
        },
        body: body ? JSON.stringify(body) : "{}",
    });
    if (r.status === 409 && artifact === "process-change-requests" && action === "approve") {
        const conflict = (await r.json().catch(() => null)) as RebaseConflict | null;
        if (conflict && Array.isArray(conflict.conflicts)) {
            throw new PcrRebaseConflictError(conflict);
        }
    }
    if (!r.ok) {
        const t = await r.text().catch(() => "");
        throw new Error(t || `HTTP ${r.status}`);
    }
    return r.json().catch(() => ({}));
}

function makeInvalidator(qc: ReturnType<typeof useQueryClient>) {
    return () => {
        qc.invalidateQueries({ queryKey: ["process-change-requests"] });
        qc.invalidateQueries({ queryKey: ["process-change-request"] });
        qc.invalidateQueries({ queryKey: ["process-change-orders"] });
        qc.invalidateQueries({ queryKey: ["process-change-order"] });
        qc.invalidateQueries({ queryKey: ["process-change-notices"] });
        qc.invalidateQueries({ queryKey: ["process-change-notice"] });
        qc.invalidateQueries({ queryKey: ["pcr-for-draft"] });
        qc.invalidateQueries({ queryKey: ["approvals"] });
    };
}

// ---- PCR ----

export type ApprovePcrResponse = {
    pcr?: Record<string, unknown>;
    pco?: Record<string, unknown>;
    rebase?: {
        rebased: boolean;
        previous_draft_id?: string | null;
        new_draft_id?: string | null;
    };
};

export function useApprovePcr() {
    const qc = useQueryClient();
    return useMutation<ApprovePcrResponse, Error, { id: string }>({
        mutationFn: ({ id }) => post("process-change-requests", id, "approve") as Promise<ApprovePcrResponse>,
        onSuccess: makeInvalidator(qc),
    });
}

export function useRejectPcr() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string; reason: string }>({
        mutationFn: ({ id, reason }) => post("process-change-requests", id, "reject", { reason }),
        onSuccess: makeInvalidator(qc),
    });
}

export function useCancelPcr() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string; reason?: string }>({
        mutationFn: ({ id, reason }) => post("process-change-requests", id, "cancel", { reason: reason ?? "" }),
        onSuccess: makeInvalidator(qc),
    });
}

// ---- PCO ----

export function useAuthorPco() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string; implementation_plan?: string; effective_date?: string | null }>({
        mutationFn: ({ id, implementation_plan, effective_date }) =>
            post("process-change-orders", id, "author", { implementation_plan, effective_date }),
        onSuccess: makeInvalidator(qc),
    });
}

export function useMarkPcoApproved() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string }>({
        mutationFn: ({ id }) => post("process-change-orders", id, "mark-approved"),
        onSuccess: makeInvalidator(qc),
    });
}

/**
 * REGULATED-mode: submit the PCO for signature collection. Creates the
 * PCO's ApprovalRequest from the tenant's PCO_APPROVAL template. The
 * PCO state doesn't change until signatures complete (the cascade
 * fires mark-approved automatically).
 */
export function useSubmitPcoForApproval() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string }>({
        mutationFn: ({ id }) => post("process-change-orders", id, "approve"),
        onSuccess: makeInvalidator(qc),
    });
}

export type MigrationDisposition = "MIGRATE_ALL" | "MIGRATE_SELECTED" | "KEEP_ALL";

export function useImplementPco() {
    const qc = useQueryClient();
    return useMutation<
        unknown,
        Error,
        { id: string; migration_disposition: MigrationDisposition; migration_reason?: string; selected_workorder_ids?: string[] }
    >({
        mutationFn: ({ id, ...rest }) => post("process-change-orders", id, "implement", rest),
        onSuccess: makeInvalidator(qc),
    });
}

export function useCancelPco() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string; reason?: string }>({
        mutationFn: ({ id, reason }) => post("process-change-orders", id, "cancel", { reason: reason ?? "" }),
        onSuccess: makeInvalidator(qc),
    });
}

// ---- PCN ----

export function useReleasePcn() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string }>({
        mutationFn: ({ id }) => post("process-change-notices", id, "release"),
        onSuccess: makeInvalidator(qc),
    });
}

export function useClosePcn() {
    const qc = useQueryClient();
    return useMutation<unknown, Error, { id: string; closure_evidence: string }>({
        mutationFn: ({ id, closure_evidence }) => post("process-change-notices", id, "close", { closure_evidence }),
        onSuccess: makeInvalidator(qc),
    });
}
