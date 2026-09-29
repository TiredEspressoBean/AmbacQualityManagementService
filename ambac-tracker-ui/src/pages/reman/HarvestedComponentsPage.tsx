import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { getCookie } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import type { QueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"HarvestedComponent">>();
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Package, Trash2, Eye, Link as LinkIcon } from "lucide-react";
import { Link } from "@tanstack/react-router";

// Default params
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

export const harvestedComponentsListOptions = () => queryOptions({
    queryKey: ["harvested-components", DEFAULT_LIST_PARAMS] as const,
    queryFn: () => api.api_HarvestedComponents_list({ queries: DEFAULT_LIST_PARAMS }),
});

// Prefetch function for route loader
export const prefetchHarvestedComponents = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(harvestedComponentsListOptions());
};

// Custom wrapper hook
function useComponentsList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    const queries: Parameters<typeof useRetrieveHarvestedComponents>[0] = { offset, limit, ...filters };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveHarvestedComponents(queries);
}

// Condition grade color mapping
function getConditionVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}

// Actions cell component
function ComponentActionsCell({ component }: { component: any }) {
    const [action, setAction] = useState<"accept" | "scrap" | null>(null);
    return (
        <>
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreHorizontal className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                    <Link to="/reman/cores/$id" params={{ id: String(component.core) }}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Source Core
                    </Link>
                </DropdownMenuItem>
                {component.component_part && (
                    <DropdownMenuItem asChild>
                        <Link to="/details/$model/$id" params={{ model: "Parts", id: String(component.component_part) }}>
                            <LinkIcon className="mr-2 h-4 w-4" />
                            View Part Record
                        </Link>
                    </DropdownMenuItem>
                )}
                {!component.is_scrapped && !component.component_part && (
                    <>
                        <DropdownMenuItem onSelect={() => setAction("accept")}>
                            <Package className="mr-2 h-4 w-4" />
                            Accept to Inventory
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive" onSelect={() => setAction("scrap")}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            Scrap Component
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
        <ComponentActionDialog component={component} action={action} onClose={() => setAction(null)} />
        </>
    );
}

/** Accept a harvested component into stock, or scrap it. Both are dispositions (lead /
 *  QA tier: accept_component, reject_component) — the teardown tech grades, someone with
 *  that authority decides. Both menu items used to have no handler at all. */
function ComponentActionDialog({ component, action, onClose }: {
    component: Schema<"HarvestedComponent">;
    action: "accept" | "scrap" | null;
    onClose: () => void;
}) {
    const qc = useQueryClient();
    const [erpId, setErpId] = useState("");
    const [reason, setReason] = useState("");
    const headers = { "X-CSRFToken": getCookie("csrftoken") };
    const done = (msg: string) => {
        toast.success(msg);
        qc.invalidateQueries({ predicate: (q) =>
            ["harvested-components", "core", "cores", "rebuildPlan"].includes(String(q.queryKey[0])) });
        setErpId(""); setReason(""); onClose();
    };
    const fail = (e: unknown, fallback: string) => {
        const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        toast.error(d ?? fallback);
    };
    const accept = useMutation({
        mutationFn: () => api.api_HarvestedComponents_accept_to_inventory_create(
            { erp_id: erpId.trim() || null }, { params: { id: String(component.id) }, headers }),
        onSuccess: (r) => done(`Accepted to stock as ${r.part_erp_id}`),
        onError: (e) => fail(e, "Could not accept the component."),
    });
    const scrap = useMutation({
        mutationFn: () => api.api_HarvestedComponents_scrap_create(
            { reason: reason.trim() }, { params: { id: String(component.id) }, headers }),
        onSuccess: () => done("Component scrapped"),
        onError: (e) => fail(e, "Could not scrap the component."),
    });
    const name = `${component.component_type_name}${component.position ? ` (${component.position})` : ""}`;

    return (
        <Dialog open={action !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
            <DialogContent>
                {action === "accept" ? (
                    <>
                        <DialogHeader>
                            <DialogTitle>Accept {name} to inventory</DialogTitle>
                            <DialogDescription>
                                Grade {component.condition_grade}, from {component.core_number}. It becomes a
                                part in stock. If its core goes back to its customer, the part is
                                reserved for that core and can't go into anyone else's rebuild.
                            </DialogDescription>
                        </DialogHeader>
                        <Input value={erpId} onChange={(e) => setErpId(e.target.value)}
                               placeholder="Part ID (optional — generated if blank)" />
                        <DialogFooter>
                            <Button variant="outline" onClick={onClose}>Cancel</Button>
                            <Button disabled={accept.isPending} onClick={() => accept.mutate()}>
                                {accept.isPending ? "Accepting…" : "Accept to inventory"}
                            </Button>
                        </DialogFooter>
                    </>
                ) : (
                    <>
                        <DialogHeader>
                            <DialogTitle>Scrap {name}</DialogTitle>
                            <DialogDescription>
                                From {component.core_number}. A scrapped component can't be accepted or
                                installed afterwards.
                            </DialogDescription>
                        </DialogHeader>
                        <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                                  placeholder="Why it can't be used" />
                        <DialogFooter>
                            <Button variant="outline" onClick={onClose}>Cancel</Button>
                            <Button variant="destructive" disabled={!reason.trim() || scrap.isPending}
                                    onClick={() => scrap.mutate()}>
                                {scrap.isPending ? "Scrapping…" : "Scrap component"}
                            </Button>
                        </DialogFooter>
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}

export function HarvestedComponentsPage() {
    return (
        <ModelEditorPage
            title="Harvested Components"
            modelName="HarvestedComponents"
            showDetailsLink={false}
            useList={useComponentsList}
            columns={[
                col({
                    header: "Component Type",
                    priority: 1,
                    renderCell: (component) => (
                        <span className="font-medium">{component.component_type_name}</span>
                    ),
                }),
                col({
                    header: "Source Core",
                    priority: 1,
                    renderCell: (component) => (
                        <Link
                            to="/reman/cores/$id"
                            params={{ id: String(component.core) }}
                            className="font-mono text-primary hover:underline"
                        >
                            {component.core_number}
                        </Link>
                    ),
                }),
                col({
                    header: "Position",
                    priority: 3,
                    renderCell: (component) => component.position || "—",
                }),
                col({
                    header: "Condition",
                    priority: 2,
                    renderCell: (component) => {
                        const grade = component.condition_grade;
                        if (!grade) return "—";
                        return (
                            <Badge variant={getConditionVariant(grade)}>
                                Grade {grade}
                            </Badge>
                        );
                    },
                }),
                col({
                    header: "Status",
                    priority: 1,
                    renderCell: (component) => {
                        if (component.is_scrapped) {
                            return <Badge variant="destructive">Scrapped</Badge>;
                        }
                        if (component.component_part) {
                            return <Badge variant="default">In Inventory</Badge>;
                        }
                        return <Badge variant="secondary">Pending</Badge>;
                    },
                }),
                col({
                    header: "Part ID",
                    priority: 2,
                    renderCell: (component) => {
                        if (component.component_part_erp_id) {
                            return (
                                <Link
                                    to="/details/$model/$id"
                                    params={{ model: "Parts", id: String(component.component_part) }}
                                    className="font-mono text-primary hover:underline"
                                >
                                    {component.component_part_erp_id}
                                </Link>
                            );
                        }
                        return "—";
                    },
                }),
                col({
                    header: "Harvested",
                    priority: 3,
                    renderCell: (component) =>
                        component.disassembled_at
                            ? format(new Date(component.disassembled_at), "MMM d, yyyy")
                            : "—",
                }),
                col({
                    header: "By",
                    priority: 4,
                    renderCell: (component) => component.disassembled_by_name || "—",
                }),
            ]}
            renderActions={(component) => <ComponentActionsCell component={component} />}
        />
    );
}

export default HarvestedComponentsPage;
