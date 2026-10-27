import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { RequestAuthorisationButton } from "@/components/reman/RequestAuthorisationButton";
import { ReportButton } from "@/components/reports/ReportButton";
import { useParams, Link, useNavigate } from "@tanstack/react-router";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { AsBuiltCard } from "@/components/reman/AsBuiltCard";
import { CorrectCoreReceiptButton } from "@/components/reman/CorrectCoreReceiptButton";
import { useCoreLifecycleAction } from "@/hooks/useReleaseCore";
import { CustomerAnswerDialog } from "@/components/WorkOrderCoresCard";
import { WorkThisUnit } from "@/components/reman/WorkThisUnit";
import { IssueCreditButton, ScrapCoreButton } from "@/components/reman/CoreLifecycleActions";
import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { coreStageLabel } from "@/lib/reman/core-stages";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { format, parseISO } from "date-fns";
import { ArrowLeft, Package, Wrench } from "lucide-react";

// Status badge variants
function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
        case 'RECEIVED': return 'secondary';
        case 'IN_DISASSEMBLY': return 'default';
        case 'DISASSEMBLED': return 'outline';
        case 'SCRAPPED': return 'destructive';
        default: return 'outline';
    }
}

function getConditionVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}


const conditionLabels: Record<string, string> = {
    'A': 'Grade A - Excellent',
    'B': 'Grade B - Good',
    'C': 'Grade C - Fair',
    'scrap': 'Scrap - Not Usable',
};

// Keys match the API's casing. They were lower-case, so every lookup missed and
// the page printed the raw enum ("CUSTOMER_RETURN") in place of every label.
const sourceLabels: Record<string, string> = {
    'CUSTOMER_RETURN': 'Customer Return',
    'PURCHASED': 'Purchased Core',
    'WARRANTY': 'Warranty Return',
    'TRADE_IN': 'Trade-In',
};

export function CoreDetailPage() {
    const { id } = useParams({ from: '/reman/cores/$id' });
    const navigate = useNavigate();
    const { data: core, isLoading, error } = useRetrieveCore(id);
    const { data: componentsData } = useRetrieveHarvestedComponents({ core: id });

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (error || !core) {
        return (
            <div className="text-center py-8">
                <p className="text-destructive">Failed to load core details</p>
                <Button variant="outline" className="mt-4" asChild>
                    <Link to="/reman/cores">Back to Cores</Link>
                </Button>
            </div>
        );
    }

    const components = componentsData?.results ?? [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link to="/reman/cores">
                            <ArrowLeft className="h-4 w-4" />
                        </Link>
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            Core {core.core_number}
                            <Badge variant={getStatusVariant(core.status || '')}>
                                {coreStageLabel(core.status)}
                            </Badge>
                            {/* Only repair-and-return is flagged here. Exchange is the
                                mode with no extra obligations, and badging both would
                                make the one that constrains the bench read as routine. */}
                            {core.returns_to_customer && (
                                <Badge variant="outline">Returns to customer</Badge>
                            )}
                        </h1>
                        <p className="text-muted-foreground">{core.core_type_name}</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    {/* The rebuild plan is the next thing that happens to a torn-down
                        core, so it is the primary action once teardown is finished. */}
                    {core.status === 'DISASSEMBLED' && (
                        <Button
                            variant="default"
                            onClick={() => navigate({ to: `/reman/cores/${id}/rebuild` })}
                        >
                            <Wrench className="mr-2 h-4 w-4" />
                            Plan rebuild
                        </Button>
                    )}
                    {core.status === 'IN_REBUILD' && core.returns_to_customer && (
                        <RequestAuthorisationButton coreId={id!} coreNumber={core.core_number} variant="outline" size="default" />
                    )}
                    {/* The over-and-above scope sheet for the customer: what work, what
                        parts, and the finding behind each — before sending, and while
                        their answer is awaited. Scope only; pricing is not UQMES's. */}
                    {core.returns_to_customer && (core.status === 'AWAITING_AUTHORISATION'
                        || (core.status === 'IN_REBUILD' && (core.authorisation_needed?.length ?? 0) > 0)) && (
                        <ReportButton reportType="over_and_above_scope" params={{ core_id: id! }}
                            label="Scope for customer" size="default" />
                    )}
                    {core.status === 'AWAITING_AUTHORISATION' && (
                        <>
                            {/* What the customer is being asked to approve, and the finding
                                behind each, is on the plan — beside the answer buttons. */}
                            <Button variant="outline" asChild>
                                <Link to="/reman/cores/$id/rebuild" params={{ id: id! }}>
                                    <Wrench className="mr-2 h-4 w-4" />
                                    Rebuild plan
                                </Link>
                            </Button>
                            <CustomerAnswerActions core={core} />
                        </>
                    )}
                    {core.status === 'RECEIVED' && <CorrectCoreReceiptButton core={core} />}
                    {core.returns_to_customer && core.authorisation_answered_at
                        && (core.status === 'IN_REBUILD' || core.status === 'DECLINED') && (
                        <CorrectAnswerButton core={core} />
                    )}
                    <WorkThisUnit core={core} />
                    <ScrapCoreButton core={core} />
                    <IssueCreditButton core={core} />
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Core Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Core Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Core Number</p>
                                <p className="font-mono font-medium">{core.core_number}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Serial Number</p>
                                <p className="font-mono">{core.serial_number || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Core Type</p>
                                <p>{core.core_type_name}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Condition</p>
                                <Badge variant={getConditionVariant(core.condition_grade)}>
                                    {conditionLabels[core.condition_grade] || core.condition_grade}
                                </Badge>
                            </div>
                        </div>
                        {core.condition_notes && (
                            <div>
                                <p className="text-sm text-muted-foreground">Condition Notes</p>
                                <p className="text-sm">{core.condition_notes}</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Source Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Source & Receipt</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Source Type</p>
                                <p>{sourceLabels[core.source_type || ''] || core.source_type}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Reference</p>
                                <p>{core.source_reference || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Customer</p>
                                <p>{core.customer_name || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">For order</p>
                                {core.order ? (
                                    <Link to="/production/orders/$orderId" params={{ orderId: String(core.order) }}
                                          className="text-primary hover:underline">
                                        {core.order_number ?? "View order"}
                                    </Link>
                                ) : (
                                    <p>—</p>
                                )}
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Fulfilment</p>
                                <p>
                                    {core.returns_to_customer
                                        ? "Repair & return — this unit goes back"
                                        : "Exchange — a unit from stock"}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Received Date</p>
                                <p>{format(parseISO(core.received_date), "PPP")}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Received By</p>
                                <p>{core.received_by_name || "—"}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Credit Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Core Credit</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Credit Value</p>
                                <p className="text-xl font-bold">
                                    {core.core_credit_value
                                        ? `$${parseFloat(core.core_credit_value).toFixed(2)}`
                                        : "Not set"}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Credit Status</p>
                                <Badge variant={core.core_credit_issued ? "default" : "secondary"}>
                                    {core.core_credit_issued ? "Issued" : "Pending"}
                                </Badge>
                            </div>
                            {core.core_credit_issued_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Issued At</p>
                                    <p>{format(new Date(core.core_credit_issued_at), "PPP p")}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Disassembly Status */}
                <Card>
                    <CardHeader>
                        <CardTitle>Work Order</CardTitle>
                        <CardDescription>
                            The job this unit is on. A core's story used to end at
                            "disassembled" — the round trip from unit to work order and
                            back is the traceability claim an audit tests.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {(core.status === 'RETURNED' || core.status === 'RETURNED_UNREPAIRED') && (
                            <p className="mb-3 text-sm">
                                <span className="text-muted-foreground">Returned </span>
                                {core.returned_at
                                    ? format(new Date(core.returned_at), "PPP")
                                    : "—"}
                                {core.return_reference && (
                                    <span className="font-mono"> · {core.return_reference}</span>
                                )}
                            </p>
                        )}
                        {core.work_order ? (
                            <div className="flex flex-wrap items-center gap-3">
                                <Link
                                    to="/workorder/$workOrderId/control"
                                    params={{ workOrderId: String(core.work_order) }}
                                    className="font-mono font-medium underline decoration-dotted underline-offset-4"
                                >
                                    {core.work_order_erp_id ?? "View work order"}
                                </Link>
                                {core.work_order_status && (
                                    <Badge variant="secondary">{core.work_order_status}</Badge>
                                )}
                                {core.status === 'IN_REBUILD' && (
                                    <Button size="sm" variant="outline" asChild>
                                        <Link to="/reman/cores/$id/rebuild" params={{ id: id! }}>
                                            <Wrench className="mr-1 h-4 w-4" />
                                            Rebuild plan
                                        </Link>
                                    </Button>
                                )}
                            </div>
                        ) : (
                            <p className="text-muted-foreground">
                                Not on a work order. Cores join one when teardown starts.
                            </p>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Disassembly Status</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Status</p>
                                <Badge variant={getStatusVariant(core.status || '')}>
                                    {coreStageLabel(core.status)}
                                </Badge>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Components Harvested</p>
                                <p className="text-xl font-bold">{components.length}</p>
                            </div>
                            {core.disassembly_started_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Started</p>
                                    <p>{format(new Date(core.disassembly_started_at), "PPP p")}</p>
                                </div>
                            )}
                            {core.disassembly_completed_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Completed</p>
                                    <p>{format(new Date(core.disassembly_completed_at), "PPP p")}</p>
                                </div>
                            )}
                            {core.disassembled_by_name && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Disassembled By</p>
                                    <p>{core.disassembled_by_name}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Harvested Components */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Harvested Components ({components.length})
                    </CardTitle>
                    <CardDescription>
                        Components extracted during disassembly
                        {core.returns_to_customer && (
                            // Every component accepted from this core is reserved to it
                            // by construction, so this is derived from the core's own
                            // mode rather than read per-part. Said here because the
                            // parts list is where someone would otherwise assume these
                            // are stock.
                            <>
                                {" — "}
                                <span className="font-medium text-foreground">
                                    reserved to this core
                                </span>
                                , and not available to other work. This unit goes back to
                                its customer, so its parts are theirs.
                            </>
                        )}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {components.length === 0 ? (
                        <p className="text-center py-8 text-muted-foreground">
                            No components harvested yet
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Component Type</TableHead>
                                    <TableHead>Position</TableHead>
                                    <TableHead>Condition</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Part ID</TableHead>
                                    <TableHead>Harvested</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {components.map((component: any) => (
                                    <TableRow key={component.id}>
                                        <TableCell className="font-medium">
                                            {component.component_type_name}
                                        </TableCell>
                                        <TableCell>{component.position || "—"}</TableCell>
                                        <TableCell>
                                            <Badge variant={getConditionVariant(component.condition_grade)}>
                                                {component.condition_grade}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {component.is_scrapped ? (
                                                <Badge variant="destructive">Scrapped</Badge>
                                            ) : component.component_part ? (
                                                <Badge variant="default">In Inventory</Badge>
                                            ) : (
                                                <Badge variant="secondary">Pending</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {component.component_part_erp_id ? (
                                                <Link
                                                    to="/details/$model/$id"
                                                    params={{ model: "Parts", id: String(component.component_part) }}
                                                    className="font-mono text-primary hover:underline"
                                                >
                                                    {component.component_part_erp_id}
                                                </Link>
                                            ) : (
                                                "—"
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {format(new Date(component.disassembled_at), "MMM d, yyyy")}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
            {core.part && <AsBuiltCard partId={String(core.part)} coreStatus={core.status} />}
            {id && (
                <div className="max-w-3xl mx-auto py-6">
                    <RecordHistoryCard endpoint="Cores" id={id} model="core" />
                </div>
            )}
        </div>
    );
}

export default CoreDetailPage;


/** The customer's answer was recorded wrong: put the right one on record, with a reason.
 *  The server refuses once the repair it authorised has started, or a declined unit has
 *  gone back. Both answers stay in the core's notes. */
function CorrectAnswerButton({ core }: { core: { id: string; core_number?: string; status?: string } }) {
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState("");
    const lifecycle = useCoreLifecycleAction();
    const wasApproved = core.status === "IN_REBUILD";
    const name = core.core_number ?? "Core";
    return (
        <>
            <Button variant="ghost" onClick={() => setOpen(true)}>Correct customer&rsquo;s answer…</Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Correct the customer&rsquo;s answer · {name}</DialogTitle>
                        <DialogDescription>
                            Recorded as <strong>{wasApproved ? "approved" : "declined"}</strong>. Correcting it to{" "}
                            <strong>{wasApproved ? "declined" : "approved"}</strong>{" "}
                            {wasApproved
                                ? "takes back the repairs that answer approved and sends the unit to Declined."
                                : "resumes the rebuild and approves the repairs that were waiting."}{" "}
                            Both answers stay in the core&rsquo;s notes. Not possible once the authorised repair has started.
                        </DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Reason"
                        placeholder="Why — e.g. keyed approved; the customer's email says decline" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={lifecycle.isPending}>Cancel</Button>
                        <Button disabled={!reason.trim() || lifecycle.isPending}
                            onClick={async () => {
                                try {
                                    await lifecycle.mutateAsync({ id: String(core.id), action: "correct_authorisation",
                                                                  approved: !wasApproved, reason: reason.trim() });
                                    toast.success(`${name} — answer corrected to ${wasApproved ? "declined" : "approved"}`);
                                    setOpen(false);
                                    setReason("");
                                } catch {
                                    // the global mutation handler shows the server's reason
                                }
                            }}>
                            Correct to {wasApproved ? "declined" : "approved"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

/** Record the customer's answer from the core itself — it waits here, so the action
 *  belongs here too (it was only on the teardown work order's card). */
function CustomerAnswerActions({ core }: { core: { id: string; core_number?: string } }) {
    const [answering, setAnswering] = useState<boolean | null>(null);
    const lifecycle = useCoreLifecycleAction();
    return (
        <>
            <Button onClick={() => setAnswering(true)} disabled={lifecycle.isPending}>Approved…</Button>
            <Button variant="outline" onClick={() => setAnswering(false)} disabled={lifecycle.isPending}>Declined…</Button>
            {answering !== null && (
                <CustomerAnswerDialog
                    coreId={String(core.id)}
                    coreNumber={core.core_number ?? "Core"}
                    approved={answering}
                    pending={lifecycle.isPending}
                    onCancel={() => setAnswering(null)}
                    onConfirm={async (fields) => {
                        try {
                            await lifecycle.mutateAsync({ id: String(core.id), action: "record_authorisation",
                                                          approved: answering, ...fields });
                            toast.success(`${core.core_number ?? "Core"} — ${answering ? "approved, rebuild resumed" : "declined"}`);
                            setAnswering(null);
                        } catch {
                            // the global mutation handler shows the server's reason
                        }
                    }}
                />
            )}
        </>
    );
}
