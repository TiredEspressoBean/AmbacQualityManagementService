import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ListChecks } from "lucide-react";
import { useListNcrs } from "@/hooks/ncrs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"NCR">>();

type View = "open" | "capa" | "all";

// A filtered list hook per view: open NCRs (the default), NCRs still waiting for the
// CAPA call (ISO 9001 10.2.1(b) — evaluated, not only acted on), or every NCR.
function useNcrList(view: View) {
    return function useList({ offset, limit, ordering, search }: {
        offset: number; limit: number; ordering?: string; search?: string;
        filters?: Record<string, string>;
    }) {
        const queries: Parameters<typeof useListNcrs>[0] = { offset, limit };
        if (ordering !== undefined) queries.ordering = ordering;
        if (search !== undefined) queries.search = search;
        if (view === "open") queries.state = "OPEN";
        if (view === "capa") queries.capa_decision__isnull = true;
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
    const [view, setView] = useState<View>("open");
    const canRaise = usePermissionSet().has("add_ncr");

    const views: { value: View; label: string }[] = [
        { value: "open", label: "Open" },
        { value: "capa", label: "Awaiting CAPA decision" },
        { value: "all", label: "All" },
    ];

    return (
        <ModelEditorPage
            title="NCRs"
            modelName="NCRs"
            listQueryKey={["ncrs"]}
            extraToolbarContent={
                <div className="flex items-center gap-1">
                    <ListChecks className="h-4 w-4 text-muted-foreground" />
                    {views.map((v) => (
                        <Button key={v.value} size="sm" variant={view === v.value ? "default" : "outline"}
                                onClick={() => setView(v.value)}>
                            {v.label}
                        </Button>
                    ))}
                </div>
            }
            useList={useNcrList(view)}
            sortOptions={[
                { label: "Opened (Newest)", value: "-created_at" },
                { label: "Opened (Oldest)", value: "created_at" },
                // Severity codes sort alphabetically: CRITICAL < MAJOR < MINOR.
                { label: "Severity (Critical First)", value: "severity" },
                { label: "Severity (Minor First)", value: "-severity" },
                { label: "Closed (Newest)", value: "-closed_at" },
            ]}
            columns={[
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
    );
}
