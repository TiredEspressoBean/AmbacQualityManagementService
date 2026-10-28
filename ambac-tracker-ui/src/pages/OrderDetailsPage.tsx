import { useEffect, useRef, useState, useMemo } from "react";
import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { orderPartsOptions } from "@/hooks/useOrderParts";
import {
    CheckCircle, Clock, Circle, ArrowLeft, Edit, UserPlus,
    Calendar, Building2, User, FileText, Package,
    Activity, ChevronDown, ChevronRight, Timer,
    CalendarClock, Users, File, Download, Image, FileSpreadsheet,
    MessageSquare, Eye, EyeOff
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { cn } from "@/lib/utils";
import { useParams, useNavigate } from "@tanstack/react-router";
import { useOrderDetails } from "@/hooks/useOrderDetails";
import { useContentTypeMapping } from "@/hooks/useContentTypes";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { api } from '@/lib/api/generated';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { InviteToOrderModal } from "@/components/invite-to-order-modal";
import { OrderLineItem } from "@/components/order-line-item";
import { OrderDocumentsModal } from "@/components/order-documents-modal";
// Demand lines. Distinct from `order-line-item` above, which is a Part row.
import { OrderLinesPanel } from "@/components/orders/OrderLinesPanel";
import { OrderShippingCard } from "@/components/orders/OrderShippingCard";
import { QuickComposer } from "@/components/QuickComposer";
import { parseDateOnly } from "@/lib/date-only";
import { deliveryCountdown } from "@/lib/delivery-countdown";
import { OrderPartsCard } from "@/components/orders/OrderPartsCard";
import { usePermissionSet } from "@/hooks/useMyPermissions";

function getStatusIcon(stage: any, size: "sm" | "md" = "md") {
    const sizeClass = size === "sm" ? "w-4 h-4" : "w-5 h-5";
    if (stage.is_completed) return <CheckCircle className={cn("text-green-500", sizeClass)} />;
    if (stage.is_current) return <Clock className={cn("text-yellow-500 animate-pulse", sizeClass)} />;
    return <Circle className={cn("text-muted-foreground/40", sizeClass)} />;
}

function getStatusBadgeVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
        case "COMPLETED":
            return "default";
        case "IN_PROGRESS":
            return "secondary";
        case "CANCELLED":
        case "ON_HOLD":
            return "destructive";
        default:
            return "outline";
    }
}

function formatStatus(status: string): string {
    return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// Component for a part type group with lazy document loading
function PartTypeGroup({
    typeName,
    parts,
    partTypeId,
    partTypesContentTypeId,
    partsContentTypeId,
}: {
    typeName: string;
    parts: any[];
    partTypeId: string | null;
    partTypesContentTypeId: number | undefined;
    partsContentTypeId: number | undefined;
}) {
    const [isOpen, setIsOpen] = useState(false);

    // Lazy fetch documents for this part type only when expanded
    const { data: typeDocsData } = useRetrieveDocuments(
        {
            content_type: partTypesContentTypeId,
            object_id: partTypeId!,
        },
        undefined,
        { enabled: !!partTypesContentTypeId && !!partTypeId && isOpen }
    );

    const typeDocuments = typeDocsData?.results || [];
    // Done includes gone: a shipped unit (or one in stock / awaiting pickup) is finished,
    // and "0/30 completed" with 10 shipped read as no progress (Customer walk).
    const DONE = new Set(["COMPLETED", "SHIPPED", "IN_STOCK", "AWAITING_PICKUP"]);
    const groupCompleted = parts.filter(p => DONE.has(p.part_status ?? "")).length;
    const groupWithIssues = parts.filter(p => p.has_error || p.quality_info?.has_errors).length;

    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <CollapsibleTrigger asChild>
                <div className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 cursor-pointer transition-colors">
                    <div className="flex items-center gap-3">
                        <ChevronRight className={cn(
                            "h-4 w-4 text-muted-foreground transition-transform duration-200",
                            isOpen && "rotate-90"
                        )} />
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="text-sm font-medium">{typeName}</h3>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                {groupCompleted}/{parts.length} completed
                                {groupWithIssues > 0 && (
                                    <span className="text-red-500 ml-2">
                                        • {groupWithIssues} issues
                                    </span>
                                )}
                            </p>
                        </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                        {parts.length}
                    </Badge>
                </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
                <div className="space-y-2 mt-2 ml-4 pl-3 border-l-2 border-muted">
                    {/* Part Type Documents */}
                    {typeDocuments.length > 0 && (
                        <div className="p-3 rounded-lg bg-muted/30 border border-dashed mb-2">
                            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-2">
                                <FileText className="h-3 w-3" />
                                Specifications & Drawings
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {typeDocuments.map((doc) => (
                                    <a
                                        key={doc.id}
                                        // file_url is null for a document row with no stored file
                                        href={doc.file_url ?? undefined}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-background border text-xs hover:bg-accent transition-colors"
                                    >
                                        {doc.is_image ? (
                                            <Image className="h-3 w-3 text-muted-foreground" />
                                        ) : doc.file_name?.endsWith('.pdf') ? (
                                            <FileText className="h-3 w-3 text-red-500" />
                                        ) : (
                                            <File className="h-3 w-3 text-muted-foreground" />
                                        )}
                                        <span className="truncate max-w-[120px]">{doc.file_name}</span>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}
                    {/* Individual Parts */}
                    {parts.map((part, index) => (
                        <OrderLineItem
                            key={part.id}
                            part={part}
                            index={index}
                            partsContentTypeId={partsContentTypeId}
                        />
                    ))}
                </div>
            </CollapsibleContent>
        </Collapsible>
    );
}


// add-note's body type. NOTE the visibility enum is uppercase -- the action
// rejects anything else (Tracker/viewsets/mes_lite.py: add_note).
type AddNoteBody = Parameters<typeof api.api_Orders_add_note_create>[0];
type NoteVisibility = NonNullable<AddNoteBody["visibility"]>;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function OrderDetailsPage() {
    const { orderNumber } = useParams({ from: "/orders/$orderNumber" });
    const navigate = useNavigate();
    const loadRef = useRef<HTMLDivElement>(null);

    const [inviteModalOpen, setInviteModalOpen] = useState(false);
    const [documentsModalOpen, setDocumentsModalOpen] = useState(false);
    const [notesExpanded, setNotesExpanded] = useState(false);
    const [noteVisibility, setNoteVisibility] = useState<NoteVisibility>("VISIBLE");

    // Opened by its order number (/orders/ORD-2024-0042): find it, then settle on its id,
    // which everything below (notes, lines, parts) addresses the order by.
    const byNumber = !UUID_RE.test(orderNumber);
    const lookup = useQuery({
        queryKey: ["order-by-number", orderNumber],
        queryFn: () => api.api_TrackerOrders_list({ queries: { order_number: orderNumber, limit: 1 } }),
        enabled: byNumber,
    });
    const foundId = lookup.data?.results?.[0]?.id;
    useEffect(() => {
        if (byNumber && foundId) {
            navigate({ to: "/orders/$orderNumber", params: { orderNumber: String(foundId) }, replace: true });
        }
    }, [byNumber, foundId, navigate]);
    const { data, isLoading: detailsLoading, error: detailsError, refetch } = useOrderDetails(byNumber ? "" : orderNumber);
    const isLoading = detailsLoading || (byNumber && (lookup.isLoading || !!foundId));
    const error = detailsError ?? (byNumber && lookup.isSuccess && !foundId ? new Error("No such order") : null);
    const perms = usePermissionSet();
    const canChangeOrders = perms.has("change_orders");
    const canAddNotes = perms.has("add_orders");

    // Mutation for adding notes
    const addNoteMutation = useMutation({
        mutationFn: async ({ message, visibility }: AddNoteBody) => {
            return await api.api_Orders_add_note_create(
                { message, visibility },
                { params: { id: orderNumber } }
            );
        },
        onSuccess: () => {
            refetch();
        },
    });

    // Get content types for fetching related documents
    const { getContentTypeId } = useContentTypeMapping();
    const ordersContentTypeId = getContentTypeId("orders");
    const partTypesContentTypeId = getContentTypeId("parttypes");
    const partsContentTypeId = getContentTypeId("parts");

    // Fetch documents related to this order
    const { data: documentsData } = useRetrieveDocuments(
        {
            content_type: ordersContentTypeId,
            object_id: orderNumber,
        },
        undefined,
        { enabled: !!ordersContentTypeId && !byNumber }
    );

    const documents = documentsData?.results || [];

    const orderId = data?.id;

    const {
        data: partsData,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
    } = useInfiniteQuery({
        ...orderPartsOptions(orderId ?? ""),
        enabled: !!orderId,
    });

    const allParts = useMemo(() => partsData?.pages.flatMap(page => page.results) ?? [], [partsData?.pages]);
    // Group parts by part type (with ID for document lookup)
    const partsByType = useMemo(() => {
        const groups: Record<string, { parts: typeof allParts; partTypeId: string | null }> = {};
        allParts.forEach(part => {
            const typeName = part.part_type_name || "Unknown Type";
            if (!groups[typeName]) {
                groups[typeName] = {
                    parts: [],
                    partTypeId: part.part_type_info?.id || part.part_type || null,
                };
            }
            groups[typeName].parts.push(part);
        });
        return groups;
    }, [allParts]);

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
                fetchNextPage();
            }
        });
        if (loadRef.current) observer.observe(loadRef.current);
        return () => observer.disconnect();
    }, [loadRef, fetchNextPage, hasNextPage, isFetchingNextPage]);

    if (isLoading) {
        return (
            <div className="max-w-5xl mx-auto p-6">
                <div className="animate-pulse space-y-6">
                    <div className="h-8 bg-muted rounded w-1/3"></div>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="h-32 bg-muted rounded"></div>
                        <div className="h-32 bg-muted rounded"></div>
                        <div className="h-32 bg-muted rounded"></div>
                    </div>
                    <div className="h-48 bg-muted rounded"></div>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="max-w-5xl mx-auto p-6">
                <Button variant="ghost" onClick={() => navigate({ to: "/editor/orders" })} className="mb-4">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Orders
                </Button>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-destructive text-center">Error loading order details.</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

     
    const {
        process_stages,
        customer_first_name,
        customer_last_name,
        estimated_completion,
        original_completion_date,
        order_status,
        order_status_code,
        company_name,
        latest_note,
        notes_timeline,
        name,
        created_at,
        parts_summary,
    } = data;

    const customerName = customer_first_name && customer_last_name
        ? `${customer_first_name} ${customer_last_name}`
        : "Unknown Customer";
    const currentStage = process_stages?.find((s: { is_current?: boolean; name?: string }) => s.is_current)?.name || "";
    const completedStages = process_stages?.filter((s: { is_completed?: boolean }) => s.is_completed).length || 0;
    const totalStages = process_stages?.length || 1;
    const progress = (completedStages / totalStages) * 100;

    // The code, not `order_status` — that is the display label ("Completed").
    const countdown = deliveryCountdown(estimated_completion, order_status_code);

    // Check if delivery date changed
    const deliveryDateChanged = original_completion_date && estimated_completion &&
        parseDateOnly(original_completion_date).getTime() !== parseDateOnly(estimated_completion).getTime();

    return (
        <div className="max-w-5xl mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate({ to: "/editor/orders" })}
                    >
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">{name || `Order #${orderNumber}`}</h1>
                        <p className="text-sm text-muted-foreground">
                            Order placed {created_at ? format(new Date(created_at), "MMMM d, yyyy") : "—"}
                        </p>
                    </div>
                    <Badge variant={getStatusBadgeVariant(order_status)} className="ml-2">
                        {formatStatus(order_status)}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setDocumentsModalOpen(true)}>
                        <File className="h-4 w-4 mr-2" />
                        Documents
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setInviteModalOpen(true)}>
                        <UserPlus className="h-4 w-4 mr-2" />
                        Invite
                    </Button>
                    {/* Offered only to those the server lets save it — a customer
                        was shown Edit and got a 403 on save. */}
                    {canChangeOrders && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate({ to: "/editor/orders/$id/edit", params: { id: orderNumber } })}
                        >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                        </Button>
                    )}
                </div>
            </div>

            {/* Hero Stats Row - Most Important Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Delivery Date - Primary Focus */}
                <Card className="md:col-span-1 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
                    <CardContent className="pt-6">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Estimated Delivery</p>
                                {estimated_completion ? (
                                    <>
                                        <p className="text-3xl font-bold tracking-tight">
                                            {format(parseDateOnly(estimated_completion), "MMM d")}
                                        </p>
                                        <p className="text-sm text-muted-foreground">
                                            {format(parseDateOnly(estimated_completion), "yyyy")}
                                        </p>
                                        {countdown && (
                                            <Badge
                                                variant={countdown.kind === "overdue" ? "destructive" : "outline"}
                                                className="mt-2"
                                            >
                                                <Timer className="h-3 w-3 mr-1" />
                                                {countdown.kind === "today"
                                                    ? "Today"
                                                    : countdown.kind === "overdue"
                                                      ? `Overdue · ${countdown.days} ${countdown.days === 1 ? "day" : "days"}`
                                                      : `${countdown.days} ${countdown.days === 1 ? "day" : "days"}`}
                                            </Badge>
                                        )}
                                        {deliveryDateChanged && (
                                            <p className="text-xs text-muted-foreground mt-2 line-through">
                                                Originally {format(parseDateOnly(original_completion_date), "MMM d, yyyy")}
                                            </p>
                                        )}
                                    </>
                                ) : (
                                    <p className="text-xl text-muted-foreground">Not set</p>
                                )}
                            </div>
                            <Calendar className="h-8 w-8 text-primary/30" />
                        </div>
                    </CardContent>
                </Card>

                {/* Progress - Visual Focus */}
                <Card className="md:col-span-1">
                    <CardContent className="pt-6">
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Progress</p>
                                <p className="text-3xl font-bold tracking-tight">{Math.round(progress)}%</p>
                            </div>
                            <Activity className="h-8 w-8 text-muted-foreground/30" />
                        </div>
                        <div className="w-full bg-muted rounded-full h-2 mb-2">
                            <div
                                className="bg-primary h-2 rounded-full transition-all duration-500"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground">
                            {completedStages} of {totalStages} stages • {currentStage && `Currently: ${currentStage}`}
                        </p>
                    </CardContent>
                </Card>

                {/* Parts Summary */}
                <Card className="md:col-span-1">
                    <CardContent className="pt-6">
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Parts</p>
                                <p className="text-3xl font-bold tracking-tight">{parts_summary?.total_parts ?? 0}</p>
                            </div>
                            <Package className="h-8 w-8 text-muted-foreground/30" />
                        </div>
                        {parts_summary && (
                            <div className="flex gap-3 text-xs">
                                <span className="text-green-600">{parts_summary.completed_parts ?? 0} done</span>
                                <span className="text-blue-600">{(parts_summary.total_parts ?? 0) - (parts_summary.completed_parts ?? 0)} remaining</span>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* What was ordered, read-only. This page is customer-facing, so it shows
                the itemisation and the dates and stops there — authoring demand and our
                planning state both live on the internal order editor
                (/editOrdersParts/$orderId). */}
            {orderId && <OrderLinesPanel orderId={orderId} readOnly />}
            {orderId && <OrderShippingCard orderId={orderId} />}

            {/* Two Column Layout for Details */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column - Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Notes Section */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center justify-between">
                                <span className="flex items-center gap-2">
                                    <MessageSquare className="h-4 w-4" />
                                    Notes
                                </span>
                                {notes_timeline && notes_timeline.length > 1 && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setNotesExpanded(!notesExpanded)}
                                    >
                                        {notesExpanded ? "Show Latest" : `Show All (${notes_timeline.length})`}
                                        <ChevronDown className={cn("h-4 w-4 ml-1 transition-transform", notesExpanded && "rotate-180")} />
                                    </Button>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* Add Note Form — the note action takes add_orders (the
                                POST default); a customer was offered it and refused. */}
                            {canAddNotes && <QuickComposer
                                placeholder="Add a note..."
                                submitting={addNoteMutation.isPending}
                                onSubmit={(message) => addNoteMutation.mutate({ message, visibility: noteVisibility })}
                                trailing={
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        onClick={() => setNoteVisibility(noteVisibility === "VISIBLE" ? "INTERNAL" : "VISIBLE")}
                                        title={noteVisibility === "VISIBLE" ? "Visible to customer" : "Internal only"}
                                    >
                                        {noteVisibility === "VISIBLE" ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                    </Button>
                                }
                            />}

                            {/* Notes Timeline */}
                            {notes_timeline && notes_timeline.length > 0 ? (
                                <div className="space-y-3">
                                    {/* `latest_note` is nullable, the timeline entries are not, so the
                                        collapsed branch drops the null here rather than relying on
                                        .filter(Boolean) -- which strips it at runtime but does not
                                        narrow the type, leaving every row typed `Note | null`. */}
                                    {(notesExpanded ? notes_timeline : latest_note ? [latest_note] : []).map((note, idx) => (
                                        <div key={idx} className="flex gap-3 text-sm">
                                            <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-primary" />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                                    <span className="font-medium text-foreground">{note.user}</span>
                                                    {note.timestamp && (
                                                        <span>
                                                            {formatDistanceToNow(new Date(note.timestamp), { addSuffix: true })}
                                                        </span>
                                                    )}
                                                    {note.visibility === "internal" && (
                                                        <Badge variant="outline" className="text-xs py-0">
                                                            <EyeOff className="h-3 w-3 mr-1" />
                                                            Internal
                                                        </Badge>
                                                    )}
                                                </div>
                                                <p className="whitespace-pre-wrap">{note.message}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground text-center py-4">
                                    No notes yet
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Line Items */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center justify-between">
                                <span className="flex items-center gap-2">
                                    <Package className="h-4 w-4" />
                                    Line Items
                                </span>
                                <span className="text-sm font-normal text-muted-foreground">
                                    {Object.keys(partsByType).length} type{Object.keys(partsByType).length !== 1 ? 's' : ''}
                                </span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {allParts.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">
                                    No parts associated with this order yet.
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    {Object.entries(partsByType).map(([typeName, { parts, partTypeId }]) => (
                                        <PartTypeGroup
                                            key={typeName}
                                            typeName={typeName}
                                            parts={parts}
                                            partTypeId={partTypeId}
                                            partTypesContentTypeId={partTypesContentTypeId}
                                            partsContentTypeId={partsContentTypeId}
                                        />
                                    ))}
                                </div>
                            )}

                            <div ref={loadRef} className="h-4 flex items-center justify-center">
                                {isFetchingNextPage && (
                                    <span className="text-xs text-muted-foreground">Loading more...</span>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column - Sidebar Info */}
                <div className="space-y-6">
                    {/* Order Details Card */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <p className="text-xs font-medium text-muted-foreground mb-1">Order Name</p>
                                <p className="text-sm font-medium">{name || `Order #${orderNumber}`}</p>
                            </div>
                            <Separator />
                            {company_name && (
                                <>
                                    <div>
                                        <p className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-1">
                                            <Building2 className="h-3 w-3" />
                                            Company
                                        </p>
                                        <p className="text-sm font-medium">{company_name}</p>
                                    </div>
                                    <Separator />
                                </>
                            )}
                            <div>
                                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-1">
                                    <User className="h-3 w-3" />
                                    Customer
                                </p>
                                <p className="text-sm font-medium">{customerName}</p>
                            </div>
                            <Separator />
                            <div>
                                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-1">
                                    <CalendarClock className="h-3 w-3" />
                                    Order Placed
                                </p>
                                <p className="text-sm font-medium">
                                    {created_at ? format(new Date(created_at), "MMM d, yyyy") : "—"}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Progress Stages - Compact */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Stages</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {process_stages?.map((stage: { is_current?: boolean; is_completed?: boolean; name?: string; [key: string]: any }, idx: number) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        {getStatusIcon(stage, "sm")}
                                        <span
                                            className={cn(
                                                "text-xs flex-1",
                                                stage.is_current
                                                    ? "font-medium text-yellow-600 dark:text-yellow-400"
                                                    : stage.is_completed
                                                        ? "text-green-600 dark:text-green-400"
                                                        : "text-muted-foreground"
                                            )}
                                        >
                                            {stage.name}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Documents */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <File className="h-3.5 w-3.5" />
                                Documents
                                {documents.length > 0 && (
                                    <Badge variant="secondary" className="text-xs ml-auto">
                                        {documents.length}
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {documents.length === 0 ? (
                                <p className="text-xs text-muted-foreground text-center py-2">
                                    No documents attached
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    {documents.map((doc) => (
                                        <a
                                            key={doc.id}
                                            // file_url is null for a document row with no stored file
                                            href={doc.file_url ?? undefined}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 transition-colors group"
                                        >
                                            {doc.is_image ? (
                                                <Image className="h-4 w-4 text-muted-foreground" />
                                            ) : doc.file_name?.endsWith('.pdf') ? (
                                                <FileText className="h-4 w-4 text-red-500" />
                                            ) : doc.file_name?.match(/\.(xlsx?|csv)$/i) ? (
                                                <FileSpreadsheet className="h-4 w-4 text-green-600" />
                                            ) : (
                                                <File className="h-4 w-4 text-muted-foreground" />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-medium truncate">{doc.file_name}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {doc.upload_date ? format(parseDateOnly(doc.upload_date), "MMM d, yyyy") : ""}
                                                </p>
                                            </div>
                                            <Download className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </a>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* People with Access */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <Users className="h-3.5 w-3.5" />
                                People
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium">
                                        {customerName.charAt(0)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium truncate">{customerName}</p>
                                        <p className="text-xs text-muted-foreground">Customer</p>
                                    </div>
                                </div>
                                {/* Everyone else given access — the card used to show only the customer. */}
                                {(data?.viewers ?? []).map((v, i) => (
                                    <div key={`${v.name}-${i}`} className="flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                                            {v.name.charAt(0)}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-medium truncate">{v.name}</p>
                                            <p className="text-xs text-muted-foreground">{v.invitation_type}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <Button variant="ghost" size="sm" className="w-full mt-3 text-xs" onClick={() => setInviteModalOpen(true)}>
                                <UserPlus className="h-3 w-3 mr-1" />
                                Invite someone
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Invite Modal */}
            <InviteToOrderModal
                open={inviteModalOpen}
                onOpenChange={setInviteModalOpen}
                orderId={orderNumber}
            />

            {/* Staff who maintain orders see — and can trim — the parts on it. The page
                is also the customer's; they don't get this card. */}
            {canChangeOrders && <OrderPartsCard orderId={orderNumber} />}

            {/* Documents Modal */}
            <OrderDocumentsModal
                open={documentsModalOpen}
                onOpenChange={setDocumentsModalOpen}
                orderId={orderNumber}
                orderName={name || `Order #${orderNumber}`}
            />
        </div>
    );
}
