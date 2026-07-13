/** Full in-app notification history — the AWARENESS surface (ephemeral,
 *  mark-read). Commitments (tasks/approvals/dispositions) live at /inbox;
 *  subscription preferences at My Notifications. */
import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Bell, CheckCheck, Settings } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    useMarkAllNotificationsRead,
    useMarkNotificationRead,
    useNotificationFeed,
    useUnreadNotificationCount,
    type NotificationFeedItem,
} from "@/hooks/notificationFeed";

export function NotificationFeedPage() {
    const navigate = useNavigate();
    const [unreadOnly, setUnreadOnly] = useState(false);
    const { data: items = [], isLoading } = useNotificationFeed({ unread: unreadOnly, limit: 100 });
    const { data: countData } = useUnreadNotificationCount();
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
        <div className="container mx-auto max-w-3xl p-6">
            <div className="mb-4 flex items-center gap-3">
                <div className="min-w-0 flex-1">
                    <h1 className="text-2xl font-bold">Notifications</h1>
                    <p className="text-muted-foreground">
                        {unread > 0 ? `${unread} unread` : "All caught up"}
                    </p>
                </div>
                <Link to="/profile/notifications">
                    <Button variant="ghost" size="sm" className="gap-1">
                        <Settings className="h-4 w-4" /> Preferences
                    </Button>
                </Link>
                {unread > 0 && (
                    <Button
                        variant="outline" size="sm" className="gap-1"
                        disabled={markAll.isPending}
                        onClick={() => markAll.mutate()}
                    >
                        <CheckCheck className="h-4 w-4" /> Mark all read
                    </Button>
                )}
            </div>

            <div className="mb-3 flex gap-2">
                <button
                    onClick={() => setUnreadOnly(false)}
                    className={`rounded-full border px-3 py-1 text-sm transition-colors ${!unreadOnly ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                >
                    All
                </button>
                <button
                    onClick={() => setUnreadOnly(true)}
                    className={`rounded-full border px-3 py-1 text-sm transition-colors ${unreadOnly ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                >
                    Unread {unread > 0 && <Badge variant="secondary" className="ml-1">{unread}</Badge>}
                </button>
            </div>

            <div className="space-y-1">
                {isLoading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
                {!isLoading && items.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <Bell className="mb-3 h-10 w-10 text-muted-foreground/30" />
                        <p className="text-sm text-muted-foreground">
                            {unreadOnly ? "Nothing unread." : "No notifications yet."}
                        </p>
                    </div>
                )}
                {items.map((n) => (
                    <button
                        key={n.id}
                        onClick={() => open(n)}
                        className="flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                    >
                        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-blue-500"}`} />
                        <span className="min-w-0 flex-1">
                            <span className={`block text-sm ${n.read_at ? "text-muted-foreground" : "font-medium"}`}>
                                {n.rendered_subject || n.event_code}
                            </span>
                            {n.rendered_body_text && (
                                <span className="mt-0.5 block text-xs text-muted-foreground line-clamp-2">
                                    {n.rendered_body_text}
                                </span>
                            )}
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                            {n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
}

export default NotificationFeedPage;