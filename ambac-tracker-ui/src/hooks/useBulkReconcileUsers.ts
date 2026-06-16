import { useMutation, useQueryClient } from "@tanstack/react-query";
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
 * `useBulkReconcileUsersStatus`.
 *
 * Raw fetch (not Zodios) because the endpoint shape isn't well-represented
 * by the auto-inferred OpenAPI body — it accepts either JSON rows OR a
 * multipart file, and the response can be 207 or 202.
 */

export type BulkReconcileRow = {
    email: string;
    first_name?: string;
    last_name?: string;
    /** Semicolon-separated for multi-group rows when coming from a workbook;
     *  single name when coming from the manual entry form. */
    group?: string;
    status?: "Active" | "Inactive";
    message?: string;
};

export type BulkReconcileResultRow = {
    row: number;
    outcome: "created" | "updated" | "unchanged" | "error";
    user_id?: string;
    invitation_id?: string;
    /** Copyable signup link for newly created users — onboarding works even
     *  when email delivery is off. Only present on `created` rows. */
    invitation_url?: string;
    changes?: string[];
    warnings?: string[];
    error?: string;
};

export type BulkReconcileSummary = {
    total: number;
    created: number;
    updated: number;
    unchanged: number;
    errors: number;
};

export type BulkReconcileResponse =
    | {
          summary: BulkReconcileSummary;
          results: BulkReconcileResultRow[];
          task_id?: never;
      }
    | {
          task_id: string;
          status: "queued";
          total_rows: number;
          message: string;
          summary?: never;
          results?: never;
      };

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
            if (r.status === 207 || r.status === 202) {
                return (await r.json()) as BulkReconcileResponse;
            }
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
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}

/** Poll a queued bulk-reconcile job by task id. */
export async function fetchBulkReconcileStatus(taskId: string): Promise<{
    task_id: string;
    status: string;
    progress?: { current: number; total: number; percent: number };
    result?: { summary: BulkReconcileSummary; results: BulkReconcileResultRow[] };
    error?: string;
}> {
    const r = await fetch(`/api/User/bulk-reconcile-status/${taskId}/`, {
        credentials: "include",
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}
