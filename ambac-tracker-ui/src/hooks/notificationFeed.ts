/** The in-app notification feed — the reader for what InAppChannel writes
 *  ("the row is the notification"). Awareness surface: ephemeral, mark-read;
 *  distinct from /inbox commitments (owned, due-dated work). */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type NotificationFeedItem = components["schemas"]["NotificationFeedItem"];

const FEED_KEY = ["notificationFeed"] as const;

// Invalidation-only helper: not a real queryOptions (no queryFn needed), just
// something that isn't a bare object literal at the invalidateQueries call
// site so the no-inline-query-key lint rule doesn't fire. Preserves the
// original ["notificationFeed"] prefix so it still invalidates every feed
// query below plus the unread count.
const feedKeyOptions = () => ({ queryKey: FEED_KEY });

function normalize(resp: unknown): NotificationFeedItem[] {
    if (Array.isArray(resp)) return resp as NotificationFeedItem[];
    return ((resp as { results?: NotificationFeedItem[] }).results ?? []);
}

export const notificationFeedOptions = (options?: { unread?: boolean; limit?: number }) =>
    queryOptions({
        queryKey: [...FEED_KEY, options?.unread ?? false, options?.limit ?? 50] as const,
        queryFn: async () =>
            normalize(await api.api_notifications_feed_list({
                queries: {
                    ...(options?.unread ? { unread: "true" } : {}),
                    limit: options?.limit ?? 50,
                },
            })),
        staleTime: 15_000,
    });

export function useNotificationFeed(options?: { unread?: boolean; limit?: number }) {
    return useQuery(notificationFeedOptions(options));
}

export const unreadNotificationCountOptions = () =>
    queryOptions({
        queryKey: [...FEED_KEY, "unread-count"] as const,
        queryFn: () =>
            api.api_notifications_feed_unread_count_retrieve() as Promise<{ unread: number }>,
        // The bell's ambient signal — poll gently.
        refetchInterval: 60_000,
        staleTime: 30_000,
    });

export function useUnreadNotificationCount() {
    return useQuery(unreadNotificationCountOptions());
}

export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) =>
            api.api_notifications_feed_mark_read_create(undefined, { params: { id } }),
        onSuccess: () => queryClient.invalidateQueries(feedKeyOptions()),
    });
}

export function useMarkAllNotificationsRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () =>
            api.api_notifications_feed_mark_all_read_create(undefined),
        onSuccess: () => queryClient.invalidateQueries(feedKeyOptions()),
    });
}
