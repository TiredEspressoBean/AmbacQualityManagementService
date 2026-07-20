/**
 * Shift notes (lead surface, /production/shift-notes) — author floor handoff
 * notes and manage recent ones. Compose uses the shared QuickComposer (the
 * "quick authoring" path); audience targets tenant groups (empty = everyone).
 * Operators read + acknowledge their active notes on the operator home.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { StickyNote, Users, X } from "lucide-react";

import { api } from "@/lib/api/generated";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { QuickComposer } from "@/components/QuickComposer";
import {
    useShiftNotes,
    usePublishShiftNote,
    useRetractShiftNote,
} from "@/hooks/shiftNotes";

export default function ShiftNotesPage() {
    const { data: notes = [] } = useShiftNotes();
    const publish = usePublishShiftNote();
    const retract = useRetractShiftNote();

    const [audience, setAudience] = useState<string[]>([]);
    const [highPriority, setHighPriority] = useState(false);
    const [ackRequired, setAckRequired] = useState(false);

    // Audience options = the tenant's groups (empty selection → everyone).
    const { data: groupPage } = useQuery({
        queryKey: ["tenant-groups", "shift-note-audience"],
        queryFn: () => api.api_TenantGroups_list({ queries: { limit: 100 } }),
    });
    const groups = groupPage?.results ?? [];

    const toggleRole = (name: string) =>
        setAudience((a) => (a.includes(name) ? a.filter((r) => r !== name) : [...a, name]));

    const submit = (body: string) => {
        publish.mutate(
            {
                body,
                audience_roles: audience,
                priority: highPriority ? "HIGH" : "NORMAL",
                acknowledgment_required: ackRequired,
            },
            {
                onSuccess: () => {
                    setAudience([]);
                    setHighPriority(false);
                    setAckRequired(false);
                    toast.success("Shift note posted.");
                },
                onError: () => toast.error("Couldn't post the note — check your access."),
            },
        );
    };

    return (
        <div className="mx-auto max-w-3xl space-y-4 p-4">
            <div>
                <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
                    <StickyNote className="h-6 w-6 text-indigo-600" /> Shift notes
                </h1>
                <p className="text-sm text-muted-foreground">
                    Hand off to the floor — operators see these on their home screen and acknowledge them.
                </p>
            </div>

            {/* Compose */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base">New note</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="h-3.5 w-3.5" /> Audience:
                        </span>
                        {audience.length === 0 && (
                            <span className="text-xs text-muted-foreground">Everyone on the floor</span>
                        )}
                        {groups.map((g) => (
                            <button
                                key={g.id}
                                type="button"
                                onClick={() => toggleRole(g.name)}
                                className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                                    audience.includes(g.name)
                                        ? "border-indigo-500 bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200"
                                        : "hover:bg-accent"
                                }`}
                            >
                                {g.name}
                            </button>
                        ))}
                        <label className="ml-auto flex cursor-pointer items-center gap-1.5 text-xs">
                            <input
                                type="checkbox"
                                checked={highPriority}
                                onChange={(e) => setHighPriority(e.target.checked)}
                            />
                            High priority
                        </label>
                        <label className="flex cursor-pointer items-center gap-1.5 text-xs">
                            <input
                                type="checkbox"
                                checked={ackRequired}
                                onChange={(e) => setAckRequired(e.target.checked)}
                            />
                            Requires acknowledgment
                        </label>
                    </div>
                    <QuickComposer
                        multiline
                        placeholder="e.g. Prioritize WO-2024-0042 before lunch — customer pickup at 2pm."
                        submitting={publish.isPending}
                        onSubmit={submit}
                    />
                </CardContent>
            </Card>

            {/* Recent */}
            <div className="space-y-2">
                <h2 className="text-sm font-medium text-muted-foreground">Recent</h2>
                {notes.length === 0 && (
                    <p className="text-sm text-muted-foreground">No shift notes yet.</p>
                )}
                {notes.map((n) => (
                    <Card key={n.id} className={n.is_voided ? "opacity-50" : ""}>
                        <CardContent className="flex items-start gap-3 py-3">
                            <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                    <span className="font-medium text-foreground">{n.author_name ?? "Lead"}</span>
                                    <span>{formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}</span>
                                    {n.priority === "HIGH" && (
                                        <Badge variant="destructive" className="text-[10px]">High</Badge>
                                    )}
                                    {n.acknowledgment_required && (
                                        <Badge className="bg-amber-500 text-[10px] text-white hover:bg-amber-500">Must ack</Badge>
                                    )}
                                    {(n.audience_roles ?? []).length === 0 ? (
                                        <Badge variant="outline" className="text-[10px]">Everyone</Badge>
                                    ) : (
                                        (n.audience_roles ?? []).map((r) => (
                                            <Badge key={r} variant="outline" className="text-[10px]">{r}</Badge>
                                        ))
                                    )}
                                    {n.work_order && n.work_order_erp_id && (
                                        <Link
                                            to="/workorder/$workOrderId"
                                            params={{ workOrderId: n.work_order }}
                                            className="font-mono text-indigo-600 underline-offset-4 hover:underline dark:text-indigo-300"
                                        >
                                            {n.work_order_erp_id}
                                        </Link>
                                    )}
                                    {n.is_voided && <Badge variant="outline" className="text-[10px]">Retracted</Badge>}
                                </div>
                                <p className="mt-1 whitespace-pre-wrap text-sm">{n.body}</p>
                                {/* Roster: must-ack notes show who's seen it (the compliance
                                    record); informational notes just show a count. */}
                                {n.acknowledgment_required ? (
                                    <div className="mt-1.5 text-xs text-muted-foreground">
                                        <span className={n.ack_count < n.audience_size ? "font-medium text-amber-600 dark:text-amber-400" : "text-green-600 dark:text-green-400"}>
                                            Acknowledged {n.ack_count} of {n.audience_size}
                                        </span>
                                        {n.acknowledged_by.length > 0 && (
                                            <span> · {n.acknowledged_by.map((a) => a.user_name).join(", ")}</span>
                                        )}
                                    </div>
                                ) : (
                                    <div className="mt-1.5 text-xs text-muted-foreground">
                                        {n.ack_count} acknowledgment{n.ack_count === 1 ? "" : "s"}
                                    </div>
                                )}
                            </div>
                            {!n.is_voided && (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 shrink-0 px-2 text-xs text-muted-foreground"
                                    disabled={retract.isPending}
                                    onClick={() => retract.mutate(n.id)}
                                >
                                    <X className="mr-1 h-3.5 w-3.5" /> Retract
                                </Button>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
