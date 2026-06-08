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
 */

type EnsureVariables = {
    partId: string;
    stepId: string;
};

type EnsureResult = {
    executionId: string;
    /** True if we had to create the row (vs found an existing one). */
    created: boolean;
};

export function useEnsureStepExecution() {
    return useMutation<EnsureResult, Error, EnsureVariables>({
        mutationFn: async ({ partId, stepId }) => {
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
            const createResp = await fetch("/api/StepExecutions/", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                body: JSON.stringify({
                    part: partId,
                    step: stepId,
                    status: "IN_PROGRESS",
                }),
            });
            if (!createResp.ok) {
                const text = await createResp.text().catch(() => "");
                throw new Error(text || `Create failed: HTTP ${createResp.status}`);
            }
            const created = await createResp.json();
            if (!created?.id) {
                throw new Error("Create returned no id");
            }
            return { executionId: String(created.id), created: true };
        },
    });
}
