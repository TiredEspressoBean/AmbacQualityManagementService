/** The bell — ambient unread count + a peek at recent notifications.
 *  Full history lives at /notifications; preferences at My Notifications. */
import { useNavigate } from "@tanstack/react-router";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
    useMarkAllNotificationsRead,
    useMarkNotificationRead,
    useNotificationFeed,
    useUnreadNotificationCount,
    type NotificationFeedItem,
} from "@/hooks/notificationFeed";

function timeAgo(iso: string | null | undefined): string {
    if (!iso) return "";
    const minutes = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60_000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${Math.round(minutes)}m ago`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
    return `${Math.round(minutes / (60 * 24))}d ago`;
}

export function NotificationBell() {
    const navigate = useNavigate();
    const { data: countData } = useUnreadNotificationCount();
    const { data: recent = [] } = useNotificationFeed({ limit: 7 });
    const markRead = useMarkNotificationRead();
    const markAll = useMarkAllNotificationsRead();

    const unread = countData?.unread ?? 0;

    const open = (item: NotificationFeedItem) => {
        if (!item.read_at) markRead.mutate(item.id);
        if (item.rendered_action_url) {
            navigate({ to: item.rendered_action_url } as never);
        }
    };

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="relative h-8 w-8" aria-label="Notifications">
                    <Bell className="h-4 w-4" />
                    {unread > 0 && (
                        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold leading-none text-white">
                            {unread > 99 ? "99+" : unread}
                        </span>
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-96 p-0" align="end">
                <div className="flex items-center justify-between border-b px-3 py-2">
                    <span className="text-sm font-medium">Notifications</span>
                    {unread > 0 && (
                        <Button
                            variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs"
                            disabled={markAll.isPending}
                            onClick={() => markAll.mutate()}
                        >
                            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
                        </Button>
                    )}
                </div>
                <div className="max-h-96 overflow-y-auto">
                    {recent.length === 0 ? (
                        <p className="p-4 text-center text-sm text-muted-foreground">Nothing yet.</p>
                    ) : (
                        recent.map((n) => (
                            <button
                                key={n.id}
                                onClick={() => open(n)}
                                className="flex w-full items-start gap-2 border-b px-3 py-2.5 text-left transition-colors last:border-b-0 hover:bg-accent"
                            >
                                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-blue-500"}`} />
                                <span className="min-w-0 flex-1">
                                    <span className={`block truncate text-sm ${n.read_at ? "text-muted-foreground" : "font-medium"}`}>
                                        {n.rendered_subject || n.event_code}
                                    </span>
                                    {n.rendered_body_text && (
                                        <span className="block truncate text-xs text-muted-foreground">
                                            {n.rendered_body_text}
                                        </span>
                                    )}
                                </span>
                                <span className="shrink-0 text-xs text-muted-foreground">{timeAgo(n.created_at)}</span>
                            </button>
                        ))
                    )}
                </div>
                <div className="border-t p-1.5">
                    <Button
                        variant="ghost" className="h-8 w-full text-xs"
                        onClick={() => navigate({ to: "/notifications" })}
                    >
                        View all
                    </Button>
                </div>
            </PopoverContent>
        </Popover>
    );
}