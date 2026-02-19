import { useState } from "react";
import { formatDistanceToNow, format } from "date-fns";
import {
    ChevronDown, ChevronRight, AlertTriangle, CheckCircle2,
    Clock, RotateCcw, Wrench, Package, Activity, File, FileText, Image, Download
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";

interface QualityInfo {
    has_errors?: boolean;
    latest_status?: string;
    error_count?: number;
}

interface Part {
    id: string;
    ERP_id: string;
    part_type_name: string | null;
    part_status: string;
    step_description: string;
    process_name: string;
    work_order_erp_id: string | null;
    quality_info: QualityInfo;
    total_rework_count: number;
    has_error: boolean;
    is_from_batch_process: boolean;
    created_at: string;
    updated_at: string;
    requires_sampling: boolean;
}

interface OrderLineItemProps {
    part: Part;
    index: number;
    partsContentTypeId?: number;
}

function formatStatus(status: string): string {
    return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function getStatusColor(status: string): string {
    switch (status) {
        case "COMPLETED":
            return "text-green-600 bg-green-50 border-green-200";
        case "IN_PROGRESS":
            return "text-blue-600 bg-blue-50 border-blue-200";
        case "PENDING":
            return "text-yellow-600 bg-yellow-50 border-yellow-200";
        case "REWORK_NEEDED":
        case "REWORK_IN_PROGRESS":
            return "text-orange-600 bg-orange-50 border-orange-200";
        case "FAILED":
        case "SCRAPPED":
            return "text-red-600 bg-red-50 border-red-200";
        default:
            return "text-gray-600 bg-gray-50 border-gray-200";
    }
}

function getQualityBadge(qualityInfo: QualityInfo, hasError: boolean) {
    if (hasError || qualityInfo?.has_errors) {
        return (
            <Badge variant="destructive" className="text-xs gap-1">
                <AlertTriangle className="h-3 w-3" />
                {qualityInfo?.error_count || 1} Issue{(qualityInfo?.error_count || 1) > 1 ? 's' : ''}
            </Badge>
        );
    }

    if (qualityInfo?.latest_status === "PASS") {
        return (
            <Badge variant="outline" className="text-xs gap-1 text-green-600 border-green-300">
                <CheckCircle2 className="h-3 w-3" />
                Passed
            </Badge>
        );
    }

    return null;
}

export function OrderLineItem({ part, index, partsContentTypeId }: OrderLineItemProps) {
    const [isOpen, setIsOpen] = useState(false);

    const timeInProduction = formatDistanceToNow(new Date(part.created_at), { addSuffix: false });
    const lastUpdated = formatDistanceToNow(new Date(part.updated_at), { addSuffix: true });

    // Fetch documents for this specific part (lazy - only when expanded)
    const { data: documentsData } = useRetrieveDocuments(
        {
            content_type: partsContentTypeId,
            object_id: part.id,
        },
        { enabled: !!partsContentTypeId && isOpen }
    );

    const partDocuments = documentsData?.results || [];

    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <CollapsibleTrigger asChild>
                <div
                    className={cn(
                        "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all",
                        "hover:bg-accent/50",
                        isOpen && "bg-accent/30 border-primary/30"
                    )}
                >
                    <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-muted text-xs font-medium">
                            {index + 1}
                        </div>
                        <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                                <p className="text-sm font-medium">{part.part_type_name || "Unknown Part"}</p>
                                {part.total_rework_count > 0 && (
                                    <Badge variant="outline" className="text-xs gap-1 text-orange-600 border-orange-300">
                                        <RotateCcw className="h-3 w-3" />
                                        {part.total_rework_count}x Rework
                                    </Badge>
                                )}
                                {getQualityBadge(part.quality_info, part.has_error)}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                {part.ERP_id} • {part.step_description || "No step"}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <Badge variant="outline" className={cn("text-xs", getStatusColor(part.part_status))}>
                            {formatStatus(part.part_status)}
                        </Badge>
                        {isOpen ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                    </div>
                </div>
            </CollapsibleTrigger>

            <CollapsibleContent>
                <div className="mt-1 ml-9 p-4 rounded-lg border border-dashed bg-muted/30 space-y-4">
                    {/* Details Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <Package className="h-3 w-3" />
                                Part ID
                            </p>
                            <p className="font-mono text-xs">{part.ERP_id}</p>
                        </div>

                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <Activity className="h-3 w-3" />
                                Process
                            </p>
                            <p className="text-xs">{part.process_name || "—"}</p>
                        </div>

                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <Wrench className="h-3 w-3" />
                                Current Step
                            </p>
                            <p className="text-xs">{part.step_description || "—"}</p>
                        </div>

                        {part.work_order_erp_id && (
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Work Order</p>
                                <p className="font-mono text-xs">{part.work_order_erp_id}</p>
                            </div>
                        )}

                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                Time in Production
                            </p>
                            <p className="text-xs">{timeInProduction}</p>
                        </div>

                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">Last Updated</p>
                            <p className="text-xs">{lastUpdated}</p>
                        </div>
                    </div>

                    {/* Quality & Sampling Section */}
                    {(part.requires_sampling || part.quality_info?.error_count > 0) && (
                        <>
                            <Separator />
                            <div className="space-y-2">
                                <p className="text-xs font-medium text-muted-foreground">Quality & Sampling</p>
                                <div className="flex flex-wrap gap-2">
                                    {part.requires_sampling && (
                                        <Badge variant="secondary" className="text-xs">
                                            Requires Sampling
                                        </Badge>
                                    )}
                                    {part.is_from_batch_process && (
                                        <Badge variant="secondary" className="text-xs">
                                            Batch Process
                                        </Badge>
                                    )}
                                    {part.quality_info?.latest_status && (
                                        <Badge
                                            variant={part.quality_info.latest_status === "PASS" ? "outline" : "destructive"}
                                            className="text-xs"
                                        >
                                            QA: {part.quality_info.latest_status}
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        </>
                    )}

                    {/* Part Documents Section */}
                    {partDocuments.length > 0 && (
                        <>
                            <Separator />
                            <div className="space-y-2">
                                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                                    <File className="h-3 w-3" />
                                    Part Documents
                                </p>
                                <div className="space-y-1">
                                    {partDocuments.map((doc: { id: string; file_url: string; file_name?: string }) => (
                                        <a
                                            key={doc.id}
                                            href={doc.file_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 transition-colors group"
                                        >
                                            {doc.is_image ? (
                                                <Image className="h-4 w-4 text-muted-foreground" />
                                            ) : doc.file_name?.endsWith('.pdf') ? (
                                                <FileText className="h-4 w-4 text-red-500" />
                                            ) : (
                                                <File className="h-4 w-4 text-muted-foreground" />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-medium truncate">{doc.file_name}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {doc.upload_date ? format(new Date(doc.upload_date), "MMM d, yyyy") : ""}
                                                </p>
                                            </div>
                                            <Download className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </a>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}

                    {/* Timestamps */}
                    <div className="text-xs text-muted-foreground pt-2 border-t">
                        Created {format(new Date(part.created_at), "MMM d, yyyy 'at' h:mm a")}
                    </div>
                </div>
            </CollapsibleContent>
        </Collapsible>
    );
}
