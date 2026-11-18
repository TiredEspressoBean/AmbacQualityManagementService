import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { Combine, ListChecks, X } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { CombineNcrsDialog, type CombinableNcr } from "@/components/quality/CombineNcrsDialog";
import { useListNcrs } from "@/hooks/ncrs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";
import type { NcrListSearchParams } from "@/lib/routes/search-params";

const col = createColumnHelper<Schema<"NCR">>();

type View = "open" | "mine" | "capa" | "all";

// A filtered list hook per view: open NCRs (the default), NCRs still waiting for the
// CAPA call (ISO 9001 10.2.1(b) — evaluated, not only acted on), or every NCR.
function useNcrList(view: View, me: number | undefined) {
    return function useList({ offset, limit, ordering, search, filters }: {
        offset: number; limit: number; ordering?: string; search?: string;
        filters?: Record<string, string>;
    }) {
        // The sidebar's filters (state, severity, CAPA decision, archived) as well.
        const queries: Parameters<typeof useListNcrs>[0] = { offset, limit, ...filters };
        if (ordering !== undefined) queries.ordering = ordering;
        if (search !== undefined) queries.search = search;
        // A view narrows; it doesn't override what the sidebar (or a link) chose.
        if ((view === "open" || view === "mine") && queries.state === undefined) queries.state = "OPEN";
        if (view === "mine" && me != null) queries.assigned_to = me;
        // A combined NCR's CAPA call is made on the one it went into.
        if (view === "capa") { queries.capa_decision__isnull = true; queries.combined_into__isnull = true; }
        return useListNcrs(queries);
    };
}

const covers = (n: Schema<"NCR">) => {
    const parts = n.members.filter((m) => m.part_id && m.held);
    if (parts.length === 1) return parts[0]!.erp_id;
    if (parts.length > 1) return `${parts.length} parts`;
    const lot = n.members.find((m) => m.lot_number);
    return lot ? `Lot ${lot.lot_number}` : "—";
};

export function NcrListPage() {
    const navigate = useNavigate();
    // The view is in the URL, so a link or a reload lands on it.
    const urlSearch = useSearch({ strict: false }) as NcrListSearchParams;
    const me = useAuthUser().data?.pk;
    // A date filter from a link ("NCRs open > 7 days"): shown, and clearable.
    const openedBefore = typeof urlSearch.created_at__lt === "string" ? urlSearch.created_at__lt : undefined;
    const clearOpenedBefore = () => navigate({
        to: "/quality/ncrs",
        search: (prev: Record<string, unknown>) => { const { created_at__lt: _drop, ...rest } = prev; return rest; },
    });
    const view: View = urlSearch.view ?? "open";
    const setView = (v: View) => navigate({
        to: "/quality/ncrs", search: (prev: Record<string, unknown>) => ({ ...prev, view: v }), replace: true,
    });
    const perms = usePermissionSet();
    const canRaise = perms.has("add_ncr");
    // Combine: open NCRs chosen here, kept across pages (change_ncr).
    const canCombine = perms.has("change_ncr");
    const [chosen, setChosen] = useState<Map<string, CombinableNcr>>(new Map());
    const [combineOpen, setCombineOpen] = useState(false);
    const toggle = (n: Schema<"NCR">) => setChosen((prev) => {
        const next = new Map(prev);
        const id = String(n.id);
        if (next.has(id)) next.delete(id);
        else next.set(id, { id, ncr_number: n.ncr_number, created_at: n.created_at, description: n.description });
        return next;
    });

    const views: { value: View; label: string }[] = [
        { value: "open", label: "Open" },
        { value: "mine", label: "Mine" },
        { value: "capa", label: "Awaiting CAPA decision" },
        { value: "all", label: "All" },
    ];

    return (
        <>
        <ModelEditorPage
            // The editor seeds its filters from the URL once: clearing the date filter starts it afresh.
            key={openedBefore ?? "all-dates"}
            // A view is a different list: start it from its first page.
            resetKey={view}
            searchPlaceholder="Search NCRs by number, description or part…"
            title="NCRs"
            modelName="NCRs"
            listQueryKey={["ncrs"]}
            extraToolbarContent={
                <div className="flex items-center gap-1">
                    {openedBefore && (
                        <span className="mr-2 inline-flex items-center gap-1 rounded-full border bg-muted px-2 py-0.5 text-xs">
                            Opened before {new Date(openedBefore).toLocaleDateString()}
                            <button type="button" onClick={clearOpenedBefore} aria-label="Clear the date filter"
                                    className="rounded-full hover:bg-background">
                                <X className="h-3 w-3" />
                            </button>
                        </span>
                    )}
                    <ListChecks className="h-4 w-4 text-muted-foreground" />
                    {views.map((v) => (
                        <Button key={v.value} size="sm" variant={view === v.value ? "default" : "outline"}
                                onClick={() => setView(v.value)}>
                            {v.label}
                        </Button>
                    ))}
                </div>
            }
            useList={useNcrList(view, me)}
            sortOptions={[
                { label: "Opened (Newest)", value: "-created_at" },
                { label: "Opened (Oldest)", value: "created_at" },
                // Severity codes sort alphabetically: CRITICAL < MAJOR < MINOR.
                { label: "Severity (Critical First)", value: "severity" },
                { label: "Severity (Minor First)", value: "-severity" },
                { label: "Closed (Newest)", value: "-closed_at" },
                { label: "Closed (Oldest)", value: "closed_at" },
            ]}
            columns={[
                ...(canCombine ? [col({
                    header: "Select",
                    priority: 1,
                    renderCell: (n) => n.state === "OPEN" ? (
                        <Checkbox
                            checked={chosen.has(String(n.id))}
                            onCheckedChange={() => toggle(n)}
                            onClick={(e) => e.stopPropagation()}
                            aria-label={`Select ${n.ncr_number}`}
                        />
                    ) : null,
                })] : []),
                col({
                    header: "NCR #",
                    renderCell: (n) => <span className="font-mono font-medium">{n.ncr_number}</span>,
                }),
                col({ header: "Covers", renderCell: covers }),
                col({
                    header: "What's wrong",
                    renderCell: (n) => (
                        <span className="max-w-[320px] truncate block" title={n.description}>
                            {n.description || <span className="text-muted-foreground">—</span>}
                        </span>
                    ),
                }),
                col({
                    header: "Severity",
                    renderCell: (n) => <StatusBadge status={n.severity} label={n.severity_display} />,
                }),
                col({
                    header: "State",
                    renderCell: (n) => <StatusBadge status={n.state} label={n.state_display} />,
                }),
                col({
                    header: "Awaiting decision",
                    priority: 2,
                    renderCell: (n) => {
                        const waiting = n.members.filter((m) => m.awaiting_decision).length;
                        return waiting ? waiting : <span className="text-muted-foreground">—</span>;
                    },
                }),
                col({
                    header: "Found at",
                    priority: 3,
                    renderCell: (n) => n.step_name ?? <span className="text-muted-foreground">—</span>,
                }),
                col({
                    header: "Opened",
                    priority: 3,
                    renderCell: (n) => new Date(n.created_at).toLocaleDateString(),
                }),
            ]}
            generateDetailLink={(n) => `/quality/ncrs/${n.id}`}
            onCreate={canRaise ? () => navigate({ to: "/quality/ncrs/new" }) : undefined}
            createLabel="Raise NCR"
        />
        {chosen.size > 0 && (
            <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
                <Card className="border-primary shadow-lg">
                    <CardContent className="flex items-center gap-2 p-3">
                        <div className="mr-2 border-r pr-2 text-sm font-medium">{chosen.size} selected</div>
                        <Button size="sm" disabled={chosen.size < 2} onClick={() => setCombineOpen(true)}>
                            <Combine className="mr-1 h-4 w-4" />
                            Combine into one NCR
                        </Button>
                        {chosen.size < 2 && (
                            <span className="text-xs text-muted-foreground">Select at least two NCRs to combine.</span>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => setChosen(new Map())} aria-label="Clear selection">
                            <X className="h-4 w-4" />
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )}
        <CombineNcrsDialog ncrs={Array.from(chosen.values())} open={combineOpen}
                           onOpenChange={setCombineOpen} onDone={() => setChosen(new Map())} />
        </>
    );
}
