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
 * work-start funnel, so the backend runs a competency check there (warn +
 * supervisor override). An unqualified start comes back as a structured
 * error (409/403/400 with a `code`); we surface it as `TrainingGateError`
 * so the caller can show the missing training and, for a supervisor, an
 * override affordance.
 */

export type TrainingGateInfo = {
    /** training_not_authorized | override_not_permitted | override_reason_required */
    code: string;
    detail: string;
    missing: { training: string; reason: string }[];
    /** Whether the CURRENT user is allowed to override the gate. */
    can_override: boolean;
};

const GATE_CODES = new Set([
    "training_not_authorized",
    "override_not_permitted",
    "override_reason_required",
]);

export class TrainingGateError extends Error {
    gate: TrainingGateInfo;
    constructor(gate: TrainingGateInfo) {
        super(gate.detail || "Not qualified for this step");
        this.name = "TrainingGateError";
        this.gate = gate;
    }
}

type EnsureVariables = {
    partId: string;
    stepId: string;
    /** Supervisor override (requires override_training_gate); pairs with reason. */
    override?: boolean;
    overrideReason?: string;
};

type EnsureResult = {
    executionId: string;
    /** True if we had to create the row (vs found an existing one). */
    created: boolean;
};

export function useEnsureStepExecution() {
    return useMutation<EnsureResult, Error, EnsureVariables>({
        mutationFn: async ({ partId, stepId, override, overrideReason }) => {
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
                body.override = true;
                body.override_reason = overrideReason ?? "";
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
        },
    });
}
