/** The in-app notification feed — the reader for what InAppChannel writes
 *  ("the row is the notification"). Awareness surface: ephemeral, mark-read;
 *  distinct from /inbox commitments (owned, due-dated work). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type NotificationFeedItem = components["schemas"]["NotificationFeedItem"];

const FEED_KEY = ["notificationFeed"] as const;

function normalize(resp: unknown): NotificationFeedItem[] {
    if (Array.isArray(resp)) return resp as NotificationFeedItem[];
    return ((resp as { results?: NotificationFeedItem[] }).results ?? []);
}

export function useNotificationFeed(options?: { unread?: boolean; limit?: number }) {
    return useQuery({
        queryKey: [...FEED_KEY, options?.unread ?? false, options?.limit ?? 50] as const,
        queryFn: async () =>
            normalize(await api.api_notifications_feed_list({
                queries: {
                    ...(options?.unread ? { unread: "true" } : {}),
                    limit: options?.limit ?? 50,
                },
            } as never)),
        staleTime: 15_000,
    });
}

export function useUnreadNotificationCount() {
    return useQuery({
        queryKey: [...FEED_KEY, "unread-count"] as const,
        queryFn: () =>
            api.api_notifications_feed_unread_count_retrieve() as Promise<{ unread: number }>,
        // The bell's ambient signal — poll gently.
        refetchInterval: 60_000,
        staleTime: 30_000,
    });
}

export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) =>
            api.api_notifications_feed_mark_read_create(undefined as never, { params: { id } }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: FEED_KEY }),
    });
}

export function useMarkAllNotificationsRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () =>
            api.api_notifications_feed_mark_all_read_create(undefined as never),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: FEED_KEY }),
    });
}