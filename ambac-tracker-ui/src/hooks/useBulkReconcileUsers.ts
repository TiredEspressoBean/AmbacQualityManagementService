import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api, schemas } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Bulk-reconcile tenant users against a desired roster.
 *
 * Backend: `POST /api/User/bulk-reconcile/` accepts either:
 *   - JSON body `{ rows: [{email, first_name, last_name, group, status, message}, ...] }`
 *   - multipart form-data `file: <.csv|.xlsx|.xls>`
 *
 * Sync below 25 rows → 207 Multi-Status with `{summary, results}`.
 * Async above 25 → 202 Accepted with `{task_id, ...}`. Poll via
 * `fetchBulkReconcileStatus`.
 *
 * Raw fetch rather than the typed client, because the REQUEST genuinely
 * can't be expressed by one Zodios operation: it is either JSON rows or a
 * multipart file, and the status code selects between two response shapes.
 *
 * The RESPONSE has no such excuse, so it is parsed through the generated Zod
 * schemas below. Previously both shapes were hand-declared here and nothing
 * checked them against the server -- including `invitation_url`, the copyable
 * signup link the roster UI falls back to when email delivery is off.
 */

// Straight from the schema, so these can't drift from the server again.
export type BulkReconcileRow = z.infer<typeof schemas.BulkReconcileRowRequest>;
export type BulkReconcileResultRow = z.infer<typeof schemas.BulkReconcileResultRow>;
export type BulkReconcileSummary = z.infer<typeof schemas.BulkReconcileSummary>;

const Queued = schemas.BulkReconcileUsersQueued;
const Synchronous = schemas.BulkReconcileUsersResponse;

export type BulkReconcileResponse =
    | (z.infer<typeof Synchronous> & { task_id?: never })
    | (z.infer<typeof Queued> & { summary?: never; results?: never });

type Variables =
    | { rows: BulkReconcileRow[]; file?: never }
    | { file: File; rows?: never };

export function useBulkReconcileUsers() {
    const queryClient = useQueryClient();
    return useMutation<BulkReconcileResponse, Error, Variables>({
        mutationFn: async (vars) => {
            const headers: Record<string, string> = {
                "X-CSRFToken": getCookie("csrftoken") ?? "",
            };
            let body: BodyInit;
            if ("file" in vars && vars.file) {
                const fd = new FormData();
                fd.append("file", vars.file);
                body = fd;
                // Don't set Content-Type — browser fills in the multipart boundary.
            } else {
                headers["Content-Type"] = "application/json";
                body = JSON.stringify({ rows: vars.rows });
            }
            const r = await fetch("/api/User/bulk-reconcile/", {
                method: "POST",
                credentials: "include",
                headers,
                body,
            });
            // 207 is the sync arm, 202 the queued one — the status code is the
            // discriminator, so each is parsed against its own schema.
            if (r.status === 207) return Synchronous.parse(await r.json());
            if (r.status === 202) return Queued.parse(await r.json());
            const text = await r.text().catch(() => "");
            throw new Error(text || `HTTP ${r.status}`);
        },
        onSuccess: () => {
            // Roster changed — refresh user lists everywhere.
            queryClient.invalidateQueries({
                predicate: (q) => {
                    const k = q.queryKey?.[0];
                    return k === "user" || k === "User";
                },
            });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "tenantGroups" });
        },
    });
}

/** The task's own early-out when it can't load the tenant or acting user.
 *
 * It RETURNS this rather than raising, so Celery records the job as SUCCESS and
 * the status endpoint hands it back in `result` — where it is not a
 * {summary, results} payload at all. Declaring only the happy shape here would
 * make the poller throw a Zod error in the browser on exactly the runs that
 * already went wrong. */
const TaskFailed = z.object({ status: z.string(), message: z.string() });

/** The Celery envelope the status endpoint wraps a finished job in. */
const BulkReconcileStatus = z.object({
    task_id: z.string(),
    status: z.string(),
    progress: z
        .object({ current: z.number(), total: z.number(), percent: z.number() })
        .optional(),
    result: z.union([Synchronous, TaskFailed]).optional(),
    error: z.string().optional(),
});

/** Narrow a finished job's `result` to the successful arm. */
export function isReconcileResult(
    result: BulkReconcileStatus["result"],
): result is z.infer<typeof Synchronous> {
    return !!result && "results" in result;
}

export type BulkReconcileStatus = z.infer<typeof BulkReconcileStatus>;

/** Poll a queued bulk-reconcile job by task id.
 *
 *  The envelope goes through the typed client now that the action declares it
 *  — it used to respond `dict`, which generated a bare passthrough object and
 *  left this a raw fetch. The local parse stays on top, and deliberately: the
 *  backend leaves `result` loose because it is polymorphic ({summary, results}
 *  on a finished run, {status, message} on the task's own early-out above), and
 *  that union is only expressible here where both arms are known. So the client
 *  checks the envelope and this narrows the payload. */
export async function fetchBulkReconcileStatus(taskId: string): Promise<BulkReconcileStatus> {
    const envelope = await api.api_User_bulk_reconcile_status_retrieve({
        params: { task_id: taskId },
    });
    return BulkReconcileStatus.parse(envelope);
}
