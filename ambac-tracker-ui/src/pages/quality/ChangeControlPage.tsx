/**
 * Change Control — list surface for PCR / PCO / PCN.
 *
 * Backend is fully built (services, viewsets, ~30 tests). This page is
 * the read-only entry point; create / lifecycle action UI lands in the
 * next pass. Three tabs read from the existing list endpoints; empty
 * states are honest about the no-data case so the sidebar entry
 * resolves to something useful even on a fresh tenant.
 */
import { FileSignature, Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    useProcessChangeRequests,
    useProcessChangeOrders,
    useProcessChangeNotices,
} from "@/hooks/useProcessChangeArtifacts";

type Row = {
    id: string;
    artifact_number?: string;
    status?: string;
    title?: string;
    created_at?: string;
    [k: string]: unknown;
};

function statusVariant(status: string | undefined): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
        case "DRAFT":
            return "outline";
        case "SUBMITTED":
        case "UNDER_REVIEW":
        case "IN_IMPLEMENTATION":
            return "secondary";
        case "APPROVED":
        case "IMPLEMENTED":
        case "RELEASED":
            return "default";
        case "REJECTED":
        case "CANCELLED":
            return "destructive";
        case "CLOSED":
            return "outline";
        default:
            return "outline";
    }
}

function ArtifactTable({
    isLoading,
    rows,
    emptyHint,
    detailPathPrefix,
}: {
    isLoading: boolean;
    rows: Row[];
    emptyHint: string;
    detailPathPrefix: string;
}) {
    const navigate = useNavigate();
    if (isLoading) {
        return (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
            </div>
        );
    }
    if (rows.length === 0) {
        return (
            <div className="p-8 text-center text-sm text-muted-foreground">{emptyHint}</div>
        );
    }
    return (
        <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left">
                <tr>
                    <th className="px-3 py-2 font-medium">Number</th>
                    <th className="px-3 py-2 font-medium">Title</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Created</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((r) => (
                    <tr
                        key={r.id}
                        className="border-t cursor-pointer hover:bg-muted/40"
                        onClick={() => { navigate({ to: `${detailPathPrefix}/${r.id}` as never }); }}
                    >
                        <td className="px-3 py-2 font-mono text-xs">{r.artifact_number ?? r.id}</td>
                        <td className="px-3 py-2">{r.title ?? "—"}</td>
                        <td className="px-3 py-2">
                            <Badge variant={statusVariant(r.status)} className="text-[10px]">
                                {r.status ?? "—"}
                            </Badge>
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                            {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

export function ChangeControlPage() {
    const [tab, setTab] = useState("requests");

    const requests = useProcessChangeRequests();
    const orders = useProcessChangeOrders();
    const notices = useProcessChangeNotices();

    const requestRows = ((requests.data as { results?: Row[] } | undefined)?.results ?? []);
    const orderRows = ((orders.data as { results?: Row[] } | undefined)?.results ?? []);
    const noticeRows = ((notices.data as { results?: Row[] } | undefined)?.results ?? []);

    return (
        <div className="container mx-auto p-6 max-w-7xl space-y-4">
            <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <FileSignature className="h-5 w-5 text-primary" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold">Change Control</h1>
                </div>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="requests">
                        Requests
                        {requestRows.length > 0 && (
                            <Badge variant="secondary" className="ml-2 text-[10px]">
                                {requestRows.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="orders">
                        Orders
                        {orderRows.length > 0 && (
                            <Badge variant="secondary" className="ml-2 text-[10px]">
                                {orderRows.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="notices">
                        Notices
                        {noticeRows.length > 0 && (
                            <Badge variant="secondary" className="ml-2 text-[10px]">
                                {noticeRows.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="requests" className="rounded-md border overflow-hidden">
                    <ArtifactTable
                        isLoading={requests.isLoading}
                        rows={requestRows}
                        emptyHint="No process change requests yet. Open a PCR from the process editor to begin a change."
                        detailPathPrefix="/quality/change-control/pcrs"
                    />
                </TabsContent>
                <TabsContent value="orders" className="rounded-md border overflow-hidden">
                    <ArtifactTable
                        isLoading={orders.isLoading}
                        rows={orderRows}
                        emptyHint="No process change orders yet. Orders are created when a PCR is approved."
                        detailPathPrefix="/quality/change-control/pcos"
                    />
                </TabsContent>
                <TabsContent value="notices" className="rounded-md border overflow-hidden">
                    <ArtifactTable
                        isLoading={notices.isLoading}
                        rows={noticeRows}
                        emptyHint="No process change notices yet. Notices are created when a PCO is implemented."
                        detailPathPrefix="/quality/change-control/pcns"
                    />
                </TabsContent>
            </Tabs>

            <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground font-mono whitespace-pre-line">
                {`This page reads existing PCR / PCO / PCN rows for the tenant. Creating a new PCR, approving, implementing, and releasing/closing are all backend-built but not yet exposed in the UI. Coming next.`}
            </div>
        </div>
    );
}
