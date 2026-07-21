import { useMutation } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Idempotent get-or-create for a `StepExecution` keyed by (part, step).
 *
 * Used by surfaces that launch the DWI operator runtime — the runtime URL
 * carries `?execution=<uuid>` and refuses to fully initialize (no
 * `ensure_inspection_qr`) without it.
 *
 * Implementation: list-first (filter by part + step), create if missing.
 * Two HTTP calls in the worst case, one in the steady state. No new
 * backend endpoint required.
 *
 * Training gate: creating the IN_PROGRESS row is the operator's real
 * work-start funnel, so the backend runs a competency check there. An
 * unqualified start comes back as a structured error (409/4xx with a `code`);
 * we surface it as `TrainingGateError` so the caller can show the missing
 * training and the supervisor re-authorization panel. Resolving it requires a
 * DIFFERENT supervisor to re-authenticate (second-person override) — passed as
 * `override.{email,password,reason}` and verified server-side.
 */

export type TrainingGateInfo = {
    /** training_not_authorized | assigned_to_other | override_auth_failed |
     *  override_self | override_not_permitted | override_reason_required |
     *  override_throttled */
    code: string;
    detail: string;
    /** Present for competence blocks; empty for a reassignment block. */
    missing?: { training: string; reason: string }[];
    /** Present for assigned_to_other — who currently holds the ticket. */
    assigned_to_name?: string;
};

const GATE_CODES = new Set([
    "training_not_authorized",
    "assigned_to_other",
    "override_auth_failed",
    "override_self",
    "override_not_permitted",
    "override_reason_required",
    "override_throttled",
]);

export class TrainingGateError extends Error {
    gate: TrainingGateInfo;
    constructor(gate: TrainingGateInfo) {
        super(gate.detail || "Not qualified for this step");
        this.name = "TrainingGateError";
        this.gate = gate;
    }
}

/** Second-person supervisor authorization for an unqualified start. */
export type OverrideCredentials = {
    email: string;
    password: string;
    reason: string;
};

type EnsureVariables = {
    partId: string;
    stepId: string;
    /** Supervisor re-auth to push past the gate (a DIFFERENT user's login). */
    override?: OverrideCredentials;
};

type EnsureResult = {
    executionId: string;
    /** True if we had to create the row (vs found an existing one). */
    created: boolean;
};

/**
 * Get-or-create + GATE the StepExecution for (part, step). Plain async (not a
 * hook) so non-render call sites — notably the serial-queue advance in
 * completion-adapters — share this ONE gated path instead of duplicating an
 * ungated copy. Both the found ("resume") and created branches go through the
 * server gate (competence + reassignment) and record the worker.
 */
export async function ensureStepExecution(
    { partId, stepId, override }: EnsureVariables,
): Promise<EnsureResult> {
    // 1. Try to find an existing execution for this (part, step).
    const listUrl =
        `/api/StepExecutions/?part=${encodeURIComponent(partId)}` +
        `&step=${encodeURIComponent(stepId)}&limit=1`;
    const listResp = await fetch(listUrl, { credentials: "include" });
    if (!listResp.ok) {
        throw new Error(`List failed: HTTP ${listResp.status}`);
    }
    const listData = await listResp.json();
    const existing = listData?.results?.[0];
    if (existing?.id) {
        // Resume path (the common case: the engine pre-creates the row).
        // Route it through `claim` so the server gates it — competence +
        // reassignment — and records the worker (assigned_to), instead of
        // silently handing back an ungated ticket. `claim` is idempotent
        // for a row already IN_PROGRESS and owned by this user.
        const claimResp = await fetch(
            `/api/StepExecutions/${existing.id}/claim/`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                body: JSON.stringify(override ? {
                    override_email: override.email,
                    override_password: override.password,
                    override_reason: override.reason,
                } : {}),
            },
        );
        if (!claimResp.ok) {
            const payload = await claimResp.json().catch(() => null);
            if (payload && GATE_CODES.has(payload.code)) {
                throw new TrainingGateError(payload as TrainingGateInfo);
            }
            const text =
                (payload && (payload.detail || JSON.stringify(payload))) ||
                `Claim failed: HTTP ${claimResp.status}`;
            throw new Error(text);
        }
        return { executionId: String(existing.id), created: false };
    }

    // 2. Not found — create one. The viewset auto-fills tenant via
    // SecureModel + middleware. visit_number defaults to 1.
    const body: Record<string, unknown> = {
        part: partId,
        step: stepId,
        status: "IN_PROGRESS",
    };
    if (override) {
        body.override_email = override.email;
        body.override_password = override.password;
        body.override_reason = override.reason;
    }
    const createResp = await fetch("/api/StepExecutions/", {
        method: "POST",
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") ?? "",
        },
        body: JSON.stringify(body),
    });
    if (!createResp.ok) {
        // The training gate answers with a structured JSON body; parse
        // it so the caller can react (missing list + override option).
        const payload = await createResp.json().catch(() => null);
        if (payload && GATE_CODES.has(payload.code)) {
            throw new TrainingGateError(payload as TrainingGateInfo);
        }
        const text =
            (payload && (payload.detail || JSON.stringify(payload))) ||
            `Create failed: HTTP ${createResp.status}`;
        throw new Error(text);
    }
    const created = await createResp.json();
    if (!created?.id) {
        throw new Error("Create returned no id");
    }
    return { executionId: String(created.id), created: true };
}

export function useEnsureStepExecution() {
    return useMutation<EnsureResult, Error, EnsureVariables>({
        mutationFn: ensureStepExecution,
    });
}
