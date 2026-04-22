import { useCallback, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { DowntimeEvent, QuarantineDisposition, CAPA } from "@/lib/api/generated";
import type { ExceptionItem, ExceptionSeverity } from "./mockData";
import { getCookie } from "@/lib/utils";

// Unified exceptions view over three real API surfaces.
//
// All three kinds now resolve WO linkage directly through their serializers:
// - DowntimeEvent exposes work_order (FK UUID | null).
// - QuarantineDisposition exposes work_order_id (UUID | null).
// - CAPA exposes work_order_ids (Array<UUID>, crawled from part + linked NCRs).

function mapQdSeverity(s: QuarantineDisposition["severity"]): ExceptionSeverity {
    switch (s) {
        case "CRITICAL":
            return "CRITICAL";
        case "MAJOR":
            return "HIGH";
        case "MINOR":
            return "LOW";
        default:
            return "MEDIUM";
    }
}

function mapCapaSeverity(s: CAPA["severity"]): ExceptionSeverity {
    switch (s) {
        case "CRITICAL":
            return "CRITICAL";
        case "MAJOR":
            return "HIGH";
        case "MINOR":
            return "LOW";
        default:
            return "MEDIUM";
    }
}

function adaptDowntime(e: DowntimeEvent): ExceptionItem {
    const woIds = e.work_order ? [e.work_order] : [];
    const label = e.equipment_name ?? e.work_center_name ?? "Equipment";
    return {
        id: e.id,
        kind: "DOWNTIME",
        title: `${label} down`,
        description: e.reason + (e.description ? ` — ${e.description}` : ""),
        severity: e.end_time == null ? "HIGH" : "MEDIUM",
        state: e.end_time == null ? "OPEN" : "RESOLVED",
        opened_at: e.start_time,
        closed_at: e.end_time ?? null,
        work_order_ids: woIds,
        reported_by: e.reported_by_name ?? "—",
        source_ref: `DowntimeEvent/${e.id}`,
    };
}

function adaptQd(q: QuarantineDisposition): ExceptionItem {
    const resolved = !!q.resolution_completed_at;
    return {
        id: q.id,
        kind: "QUARANTINE",
        title: `${q.disposition_number} · ${q.severity_display ?? "Quarantine"}`,
        description: q.description ?? q.containment_action ?? "",
        severity: mapQdSeverity(q.severity),
        state: q.current_state ?? (resolved ? "RESOLVED" : "OPEN"),
        opened_at: q.containment_completed_at ?? q.resolution_completed_at ?? new Date().toISOString(),
        closed_at: resolved ? q.resolution_completed_at ?? null : null,
        work_order_ids: q.work_order_id ? [q.work_order_id] : [],
        reported_by: q.assignee_name ?? "—",
        source_ref: `QuarantineDisposition/${q.id}`,
    };
}

function adaptCapa(c: CAPA): ExceptionItem {
    const isClosed = !!c.completed_date;
    return {
        id: c.id,
        kind: "CAPA",
        title: `${c.capa_number} · ${c.capa_type_display}`,
        description: c.problem_statement,
        severity: mapCapaSeverity(c.severity),
        state: c.status_display ?? c.status,
        opened_at: c.initiated_date,
        closed_at: isClosed ? c.completed_date : null,
        work_order_ids: c.work_order_ids,
        reported_by: (c.initiated_by_info as { name?: string })?.name ?? "—",
        source_ref: `CAPA/${c.id}`,
    };
}

export function useExceptions() {
    const dt = useQuery({
        queryKey: ["downtime-events", { limit: 200 }],
        queryFn: () => api.api_DowntimeEvents_list({ queries: { limit: 200 } }),
    });
    const qd = useQuery({
        queryKey: ["quarantine-dispositions", { limit: 200 }],
        queryFn: () => api.api_QuarantineDispositions_list({ queries: { limit: 200 } }),
    });
    const capas = useQuery({
        queryKey: ["capas", { limit: 200 }],
        queryFn: () => api.api_CAPAs_list({ queries: { limit: 200 } }),
    });

    const items = useMemo<ExceptionItem[]>(() => {
        const out: ExceptionItem[] = [];
        (dt.data?.results ?? []).forEach((e) => out.push(adaptDowntime(e)));
        (qd.data?.results ?? []).forEach((e) => out.push(adaptQd(e)));
        (capas.data?.results ?? []).forEach((e) => out.push(adaptCapa(e)));
        return out;
    }, [dt.data, qd.data, capas.data]);

    const queryClient = useQueryClient();
    const { mutateAsync: resolveDowntimeAsync } = useMutation({
        mutationFn: (id: string) =>
            api.api_DowntimeEvents_resolve_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["downtime-events"] });
        },
    });

    // Resolve an exception via its native verb. Only Downtime has a real
    // resolve endpoint today; QD and CAPA close via status patches elsewhere.
    const resolveException = useCallback(
        (id: string, kind: ExceptionItem["kind"]) => {
            if (kind === "DOWNTIME" && /^[0-9a-f-]{36}$/i.test(id)) {
                void resolveDowntimeAsync(id).catch(() => {});
            }
        },
        [resolveDowntimeAsync],
    );

    return {
        data: items,
        isLoading: dt.isLoading || qd.isLoading || capas.isLoading,
        error: dt.error ?? qd.error ?? capas.error ?? null,
        resolveException,
    };
}
