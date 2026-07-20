/** Shift notes — human-authored floor handoff. Distinct from the notification
 *  feed: authored by a person, aimed at an audience, acknowledged by readers.
 *  `active` is the operator's self-scoped feed (audience ∩ effective ∩ un-acked);
 *  the plain list is the lead's management view. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type ShiftNote = components["schemas"]["ShiftNote"];
export type ShiftNoteRequest = components["schemas"]["ShiftNoteRequest"];

const KEY = ["shiftNotes"] as const;

/** The current operator's active notes (paginated envelope → flat list). */
export function useActiveShiftNotes() {
    return useQuery({
        queryKey: [...KEY, "active"] as const,
        queryFn: async () => (await api.api_ShiftNotes_active_list()).results ?? [],
        staleTime: 15_000,
    });
}

/** All notes (lead management view), newest first. */
export function useShiftNotes(limit = 50) {
    return useQuery({
        queryKey: [...KEY, "list", limit] as const,
        queryFn: async () =>
            (await api.api_ShiftNotes_list({ queries: { limit, ordering: "-created_at" } })).results ?? [],
    });
}

export function usePublishShiftNote() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body: ShiftNoteRequest) => api.api_ShiftNotes_create(body),
        onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
    });
}

export function useAcknowledgeShiftNote() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id: string) =>
            api.api_ShiftNotes_acknowledge_create(undefined as never, { params: { id } }),
        onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
    });
}

export function useRetractShiftNote() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id: string) =>
            api.api_ShiftNotes_retract_create(undefined as never, { params: { id } }),
        onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
    });
}
