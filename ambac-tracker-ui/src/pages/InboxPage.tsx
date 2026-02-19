import { useState, useCallback } from "react";
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    CheckSquare,
    ClipboardList,
    FileSignature,
    Calendar,
    AlertTriangle,
    Clock,
    CalendarDays,
    ChevronDown,
    ChevronRight,
    Check,
    ExternalLink,
    Paperclip,
    FileText,
} from "lucide-react";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// Hooks
import { useMyCapaTasks, type CapaTask } from "@/hooks/useMyCapaTasks";
import { useMyPendingApprovals, type PendingApproval } from "@/hooks/useMyPendingApprovals";
import { useCompleteCapaTask } from "@/hooks/useCompleteCapaTask";
import { useSubmitApprovalResponse } from "@/hooks/useSubmitApprovalResponse";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { useQueryClient } from "@tanstack/react-query";

// Components
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader";
import {
    SignatureVerification,
    validateSignatureVerification,
    type SignatureVerificationData,
} from "@/components/approval/SignatureVerification";
import { Alert, AlertDescription } from "@/components/ui/alert";

// ============================================================================
// TYPES
// ============================================================================

type InboxItemType = "capa_task" | "approval";
type UrgencyLevel = "overdue" | "due_today" | "due_this_week" | "upcoming";

interface InboxItem {
    id: string;
    numericId: number;
    type: InboxItemType;
    title: string;
    subtitle?: string;  // Secondary info like task type or content object
    description?: string;
    reference: string;
    referenceUrl: string;
    dueDate?: Date;
    assignedTo?: string;  // Who the task is assigned to (for tasks)
    requestedBy?: string; // Who requested approval (for approvals)
    status: string;
    statusDisplay: string;
    isOverdue: boolean;
    createdAt: Date;
    // Original data for mutations
    originalTask?: CapaTask;
    originalApproval?: PendingApproval;
}

// ============================================================================
// DATA TRANSFORMATION
// ============================================================================

function transformCapaTask(task: CapaTask): InboxItem {
    return {
        id: `task-${task.id}`,
        numericId: task.id,
        type: "capa_task",
        title: task.description || "Untitled Task",
        subtitle: task.task_type_display,  // "Corrective Action", "Preventive Action"
        description: task.capa_info?.description,
        reference: task.capa_info?.capa_number || `CAPA #${task.capa}`,
        referenceUrl: `/quality/capas/${task.capa}`,
        dueDate: task.due_date ? new Date(task.due_date) : undefined,
        assignedTo: task.assigned_to_info?.full_name || task.assigned_to_info?.username,
        status: task.status,
        statusDisplay: task.status_display,
        isOverdue: task.is_overdue,
        createdAt: new Date(task.created_at),
        originalTask: task,
    };
}

function transformApproval(approval: PendingApproval): InboxItem {
    // Calculate is_overdue from due_date
    const isOverdue = approval.due_date
        ? new Date(approval.due_date) < new Date()
        : false;

    return {
        id: `approval-${approval.id}`,
        numericId: approval.id,
        type: "approval",
        title: approval.content_object_info?.str || approval.reason || "Approval Request",
        subtitle: approval.approval_type_display,  // "CAPA Approval", "Document Approval"
        reference: approval.approval_number,
        referenceUrl: getApprovalReferenceUrl(approval),
        dueDate: approval.due_date ? new Date(approval.due_date) : undefined,
        requestedBy: approval.requested_by_info?.full_name || approval.requested_by_info?.username,
        status: approval.status,
        statusDisplay: approval.status_display,
        isOverdue,
        createdAt: new Date(approval.requested_at),
        originalApproval: approval,
    };
}

function getApprovalReferenceUrl(approval: PendingApproval): string {
    // Route to appropriate detail page based on content object type
    const contentType = approval.content_object_info?.type?.toLowerCase();

    if (contentType === "capa") {
        return `/quality/capas/${approval.object_id}`;
    }
    if (contentType === "documents" || contentType === "document") {
        return `/documents/${approval.object_id}`;
    }
    // Fallback: try to infer from approval_type
    if (approval.approval_type.includes("CAPA")) {
        return `/quality/capas/${approval.object_id}`;
    }
    if (approval.approval_type.includes("DOCUMENT")) {
        return `/documents/${approval.object_id}`;
    }
    return "#";
}

// ============================================================================
// HELPERS
// ============================================================================

function getUrgencyLevel(dueDate?: Date, isOverdue?: boolean): UrgencyLevel {
    if (isOverdue) return "overdue";
    if (!dueDate) return "upcoming";

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const endOfToday = new Date(startOfToday.getTime() + 24 * 60 * 60 * 1000 - 1);
    const endOfWeek = new Date(startOfToday.getTime() + 7 * 24 * 60 * 60 * 1000);

    if (dueDate < startOfToday) return "overdue";
    if (dueDate <= endOfToday) return "due_today";
    if (dueDate <= endOfWeek) return "due_this_week";
    return "upcoming";
}

function formatDueDate(dueDate?: Date, isOverdue?: boolean): string {
    if (!dueDate) return "No due date";

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffDays = Math.floor((dueDate.getTime() - startOfToday.getTime()) / (24 * 60 * 60 * 1000));

    if (isOverdue || diffDays < 0) {
        const overdueDays = Math.abs(diffDays);
        return overdueDays === 1 ? "1 day overdue" : `${overdueDays} days overdue`;
    }
    if (diffDays === 0) return "Due today";
    if (diffDays === 1) return "Due tomorrow";
    if (diffDays <= 7) return `Due in ${diffDays} days`;
    return `Due ${dueDate.toLocaleDateString()}`;
}

function groupByUrgency(items: InboxItem[]): Record<UrgencyLevel, InboxItem[]> {
    const groups: Record<UrgencyLevel, InboxItem[]> = {
        overdue: [],
        due_today: [],
        due_this_week: [],
        upcoming: [],
    };

    items.forEach(item => {
        const urgency = getUrgencyLevel(item.dueDate, item.isOverdue);
        groups[urgency].push(item);
    });

    // Sort each group by due date
    Object.keys(groups).forEach(key => {
        groups[key as UrgencyLevel].sort((a, b) => {
            if (!a.dueDate) return 1;
            if (!b.dueDate) return -1;
            return a.dueDate.getTime() - b.dueDate.getTime();
        });
    });

    return groups;
}

// ============================================================================
// CONFIG
// ============================================================================

const urgencyConfig: Record<UrgencyLevel, { label: string; icon: React.ElementType; className: string }> = {
    overdue: { label: "Overdue", icon: AlertTriangle, className: "text-destructive" },
    due_today: { label: "Due Today", icon: Clock, className: "text-amber-600" },
    due_this_week: { label: "This Week", icon: CalendarDays, className: "text-blue-600" },
    upcoming: { label: "Upcoming", icon: Calendar, className: "text-muted-foreground" },
};

const typeConfig: Record<InboxItemType, { icon: React.ElementType; bgColor: string; iconColor: string }> = {
    capa_task: { icon: ClipboardList, bgColor: "bg-primary/10", iconColor: "text-primary" },
    approval: { icon: FileSignature, bgColor: "bg-amber-100 dark:bg-amber-900/30", iconColor: "text-amber-700 dark:text-amber-400" },
};

// ============================================================================
// MODALS
// ============================================================================

function CompleteTaskModal({
    open,
    onOpenChange,
    item,
    onComplete,
    isSubmitting,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    item: InboxItem;
    onComplete: (data: { notes: string; signature_data?: string; password?: string }) => void;
    isSubmitting: boolean;
}) {
    const [notes, setNotes] = useState("");
    const [showUploader, setShowUploader] = useState(false);
    const [signatureVerification, setSignatureVerification] = useState<SignatureVerificationData>({
        signature_data: "",
        password: "",
        confirmed: false,
    });
    const [error, setError] = useState<string | null>(null);

    // Get content type ID for CapaTasks
    const { data: contentTypes } = useRetrieveContentTypes({});
    const contentTypesList = Array.isArray(contentTypes) ? contentTypes : contentTypes?.results;
    const capaTasksContentType = contentTypesList?.find(
        (ct: any) => ct.model === "capatasks" && ct.app_label === "Tracker"
    );

    const existingDocs = item.originalTask?.documents_info;
    const requiresSignature = item.originalTask?.requires_signature ?? false;

    const handleSignatureChange = useCallback((data: SignatureVerificationData) => {
        setSignatureVerification(data);
    }, []);

    const handleSubmit = () => {
        setError(null);

        // Validate signature requirements
        if (requiresSignature) {
            const validationError = validateSignatureVerification(signatureVerification);
            if (validationError) {
                setError(validationError);
                return;
            }
        }

        onComplete({
            notes,
            signature_data: requiresSignature ? signatureVerification.signature_data : undefined,
            password: requiresSignature ? signatureVerification.password : undefined,
        });

        // Reset form
        setNotes("");
        setSignatureVerification({ signature_data: "", password: "", confirmed: false });
        setShowUploader(false);
        setError(null);
    };

    const handleClose = () => {
        setNotes("");
        setSignatureVerification({ signature_data: "", password: "", confirmed: false });
        setShowUploader(false);
        setError(null);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Complete Task</DialogTitle>
                    <DialogDescription>
                        Mark this task as complete and add any notes about what was done.
                        {requiresSignature && (
                            <span className="block mt-1 text-amber-600">
                                This task requires signature verification.
                            </span>
                        )}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label className="text-muted-foreground">Task</Label>
                        <p className="font-medium">{item.title}</p>
                        <p className="text-sm text-muted-foreground">{item.reference}</p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="completion-notes">Completion Notes</Label>
                        <Textarea
                            id="completion-notes"
                            placeholder="Describe what was done to complete this task..."
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            rows={4}
                        />
                    </div>

                    {/* Existing Documents */}
                    {existingDocs && existingDocs.count > 0 && (
                        <div className="space-y-2">
                            <Label className="flex items-center gap-2">
                                <Paperclip className="h-4 w-4" />
                                Attached Evidence ({existingDocs.count})
                            </Label>
                            <div className="space-y-1">
                                {existingDocs.items.map((doc) => (
                                    <a
                                        key={doc.id}
                                        href={doc.file_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-2 text-sm text-primary hover:underline"
                                    >
                                        <FileText className="h-3 w-3" />
                                        {doc.file_name}
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Document Upload Section */}
                    <div className="space-y-2 border-t pt-4">
                        {!showUploader ? (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setShowUploader(true)}
                                className="gap-2"
                            >
                                <Paperclip className="h-4 w-4" />
                                Attach Evidence
                            </Button>
                        ) : capaTasksContentType ? (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label>Upload Evidence</Label>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setShowUploader(false)}
                                    >
                                        Cancel
                                    </Button>
                                </div>
                                <DocumentUploader
                                    objectId={item.numericId}
                                    contentType={capaTasksContentType.id.toString()}
                                />
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                Loading document upload...
                            </p>
                        )}
                    </div>

                    {/* Signature Verification Section (only if required) */}
                    {requiresSignature && (
                        <div className="border-t pt-4">
                            <SignatureVerification
                                onChange={handleSignatureChange}
                                confirmationText="I confirm this is my signature and I have completed all required actions for this task."
                                passwordHelpText="Your password is required to verify your identity for this completion."
                                error={error}
                            />
                        </div>
                    )}

                    {/* Error message (only show if no signature section, otherwise it shows in SignatureVerification) */}
                    {!requiresSignature && error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={isSubmitting}>
                        {isSubmitting ? "Completing..." : "Complete Task"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function ApprovalModal({
    open,
    onOpenChange,
    item,
    onApprove,
    onReject,
    isSubmitting,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    item: InboxItem;
    onApprove: (comments: string) => void;
    onReject: (comments: string) => void;
    isSubmitting: boolean;
}) {
    const [comments, setComments] = useState("");
    const [confirmed, setConfirmed] = useState(false);

    const handleApprove = () => {
        if (!confirmed) {
            toast.error("Please confirm you have reviewed this item");
            return;
        }
        onApprove(comments);
        setComments("");
        setConfirmed(false);
    };

    const handleReject = () => {
        if (!comments.trim()) {
            toast.error("Please provide a reason for rejection");
            return;
        }
        onReject(comments);
        setComments("");
        setConfirmed(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Review Approval</DialogTitle>
                    <DialogDescription>
                        Review and approve or reject this request.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label className="text-muted-foreground">Request</Label>
                        <p className="font-medium">{item.title}</p>
                        <p className="text-sm text-muted-foreground">{item.reference}</p>
                        {item.description && (
                            <p className="text-sm text-muted-foreground mt-2">{item.description}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="approval-comments">Comments (required for rejection)</Label>
                        <Textarea
                            id="approval-comments"
                            placeholder="Add any comments..."
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            rows={3}
                        />
                    </div>

                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="confirm-review"
                            checked={confirmed}
                            onCheckedChange={(checked) => setConfirmed(checked as boolean)}
                        />
                        <Label htmlFor="confirm-review" className="text-sm font-normal">
                            I confirm I have reviewed this item
                        </Label>
                    </div>
                </div>

                <DialogFooter className="flex gap-2 sm:gap-0">
                    <Button variant="destructive" onClick={handleReject} disabled={isSubmitting}>
                        Reject
                    </Button>
                    <div className="flex-1" />
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
                        Cancel
                    </Button>
                    <Button onClick={handleApprove} disabled={isSubmitting || !confirmed}>
                        {isSubmitting ? "Submitting..." : "Approve"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================================
// INBOX ITEM CARD
// ============================================================================

function InboxItemCard({ item }: { item: InboxItem }) {
    const [showCompleteModal, setShowCompleteModal] = useState(false);
    const [showApprovalModal, setShowApprovalModal] = useState(false);

    const queryClient = useQueryClient();
    const completeTask = useCompleteCapaTask();
    const submitApproval = useSubmitApprovalResponse(item.numericId);

    const typeInfo = typeConfig[item.type];
    const TypeIcon = typeInfo.icon;

    const handleCompleteTask = (data: { notes: string; signature_data?: string; password?: string }) => {
        completeTask.mutate(
            {
                id: item.numericId,
                data: {
                    completion_notes: data.notes,
                    signature_data: data.signature_data,
                    password: data.password,
                }
            },
            {
                onSuccess: () => {
                    toast.success(`Task completed: ${item.title}`);
                    setShowCompleteModal(false);
                    queryClient.invalidateQueries({ queryKey: ["capa-my-tasks"] });
                },
                onError: (error: any) => {
                    const message = error?.response?.data?.error || "Failed to complete task";
                    toast.error(message);
                    console.error(error);
                },
            }
        );
    };

    const handleApprove = (comments: string) => {
        submitApproval.mutate(
            { decision: "APPROVED", comments },
            {
                onSuccess: () => {
                    toast.success(`Approved: ${item.title}`);
                    setShowApprovalModal(false);
                    queryClient.invalidateQueries({ queryKey: ["approvals", "my-pending"] });
                },
                onError: (error) => {
                    toast.error("Failed to submit approval");
                    console.error(error);
                },
            }
        );
    };

    const handleReject = (comments: string) => {
        submitApproval.mutate(
            { decision: "REJECTED", comments },
            {
                onSuccess: () => {
                    toast.success(`Rejected: ${item.title}`);
                    setShowApprovalModal(false);
                    queryClient.invalidateQueries({ queryKey: ["approvals", "my-pending"] });
                },
                onError: (error) => {
                    toast.error("Failed to submit rejection");
                    console.error(error);
                },
            }
        );
    };

    const isSubmitting = completeTask.isPending || submitApproval.isPending;

    return (
        <>
            <div className="flex gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                {/* Icon */}
                <div className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg mt-0.5",
                    typeInfo.bgColor
                )}>
                    <TypeIcon className={cn("h-5 w-5", typeInfo.iconColor)} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-1">
                    {/* Title row with subtitle badge */}
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium line-clamp-1">{item.title}</span>
                        {item.subtitle && (
                            <Badge variant="outline" className="text-xs shrink-0">
                                {item.subtitle}
                            </Badge>
                        )}
                        <span className="text-sm font-mono text-muted-foreground ml-auto shrink-0">
                            {item.reference}
                        </span>
                    </div>

                    {/* Description - for tasks, show CAPA description */}
                    {item.description && (
                        <p className="text-sm text-muted-foreground line-clamp-1">
                            {item.description}
                        </p>
                    )}

                    {/* Meta row */}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        {item.assignedTo && (
                            <span>assigned to {item.assignedTo}</span>
                        )}
                        {item.requestedBy && (
                            <span>from {item.requestedBy}</span>
                        )}
                        <Badge
                            variant="secondary"
                            className={cn(
                                "text-xs",
                                item.status === "IN_PROGRESS" && "bg-blue-100 text-blue-800",
                                item.status === "PENDING" && "bg-yellow-100 text-yellow-800",
                            )}
                        >
                            {item.statusDisplay}
                        </Badge>
                        {item.dueDate && (
                            <span className={cn(
                                "flex items-center gap-1 ml-auto",
                                item.isOverdue && "text-destructive font-medium"
                            )}>
                                <Calendar className="h-3 w-3" />
                                {formatDueDate(item.dueDate, item.isOverdue)}
                            </span>
                        )}
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                    <Button size="sm" variant="ghost" className="h-8 gap-1 text-muted-foreground" asChild>
                        <Link to={item.referenceUrl}>
                            <ExternalLink className="h-3 w-3" />
                            View
                        </Link>
                    </Button>
                    {item.type === "approval" ? (
                        <Button
                            size="sm"
                            variant="default"
                            className="h-8 gap-1"
                            onClick={() => setShowApprovalModal(true)}
                            disabled={isSubmitting}
                        >
                            <FileSignature className="h-3 w-3" />
                            Review
                        </Button>
                    ) : (
                        <Button
                            size="sm"
                            variant="outline"
                            className="h-8 gap-1"
                            onClick={() => setShowCompleteModal(true)}
                            disabled={isSubmitting}
                        >
                            <Check className="h-3 w-3" />
                            Complete
                        </Button>
                    )}
                </div>
            </div>

            {/* Modals */}
            <CompleteTaskModal
                open={showCompleteModal}
                onOpenChange={setShowCompleteModal}
                item={item}
                onComplete={handleCompleteTask}
                isSubmitting={completeTask.isPending}
            />
            <ApprovalModal
                open={showApprovalModal}
                onOpenChange={setShowApprovalModal}
                item={item}
                onApprove={handleApprove}
                onReject={handleReject}
                isSubmitting={submitApproval.isPending}
            />
        </>
    );
}

// ============================================================================
// URGENCY SECTION
// ============================================================================

function UrgencySection({
    urgency,
    items,
    defaultOpen = true,
}: {
    urgency: UrgencyLevel;
    items: InboxItem[];
    defaultOpen?: boolean;
}) {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    const config = urgencyConfig[urgency];
    const Icon = config.icon;

    if (items.length === 0) return null;

    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 hover:bg-muted/50 rounded-md px-2 -mx-2">
                {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
                <Icon className={cn("h-4 w-4", config.className)} />
                <span className={cn("font-medium text-sm", config.className)}>
                    {config.label}
                </span>
                <Badge variant="secondary" className="ml-auto">
                    {items.length}
                </Badge>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 pt-2">
                {items.map(item => (
                    <InboxItemCard key={item.id} item={item} />
                ))}
            </CollapsibleContent>
        </Collapsible>
    );
}

// ============================================================================
// LOADING & EMPTY STATES
// ============================================================================

function LoadingSkeleton() {
    return (
        <div className="space-y-4">
            {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-4 p-4 border rounded-lg">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                        <Skeleton className="h-3 w-1/4" />
                    </div>
                    <Skeleton className="h-8 w-20" />
                </div>
            ))}
        </div>
    );
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <CheckSquare className="h-12 w-12 text-muted-foreground/30 mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground">All clear!</h3>
            <p className="text-sm text-muted-foreground/70 mt-1">
                You have no pending tasks or approvals.
            </p>
        </div>
    );
}

// ============================================================================
// MOCK DATA - Toggle this flag to use mock data instead of API
// ============================================================================

const USE_MOCK_DATA = false;

// Mock data matching the actual API serializer structure
const MOCK_TASKS: CapaTask[] = [
    {
        id: 1,
        task_number: "TASK-2024-001",
        capa: 101,
        capa_info: {
            id: 101,
            capa_number: "CAPA-2024-001",
            description: "Root cause analysis for dimensional deviation on Part #A1234",
        },
        task_type: "CORRECTIVE",
        task_type_display: "Corrective Action",
        description: "Implement SPC monitoring for critical dimensions",
        assigned_to: 1,
        assigned_to_info: {
            id: 1,
            username: "jsmith",
            full_name: "John Smith",
        },
        completion_mode: "SINGLE",
        completion_mode_display: "Single Approver",
        due_date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 2 days ago (overdue)
        status: "IN_PROGRESS",
        status_display: "In Progress",
        is_overdue: true,
        requires_signature: true, // High-risk corrective action requires signature
        documents_info: {
            count: 2,
            items: [
                { id: 1001, file_name: "SPC_Control_Chart_Setup.pdf", file_url: "/media/docs/spc_setup.pdf", upload_date: "2024-12-05T10:30:00Z" },
                { id: 1002, file_name: "Dimension_Analysis_Report.xlsx", file_url: "/media/docs/analysis.xlsx", upload_date: "2024-12-06T14:15:00Z" },
            ],
        },
        created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 2,
        task_number: "TASK-2024-002",
        capa: 102,
        capa_info: {
            id: 102,
            capa_number: "CAPA-2024-002",
            description: "Process improvement for surface finish quality",
        },
        task_type: "PREVENTIVE",
        task_type_display: "Preventive Action",
        description: "Update work instructions for finishing process",
        assigned_to: 1,
        assigned_to_info: {
            id: 1,
            username: "jsmith",
            full_name: "John Smith",
        },
        completion_mode: "SINGLE",
        completion_mode_display: "Single Approver",
        due_date: new Date().toISOString().split('T')[0], // Today
        status: "PENDING",
        status_display: "Pending",
        is_overdue: false,
        requires_signature: false, // Lower-risk preventive action
        documents_info: {
            count: 0,
            items: [],
        },
        created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 3,
        task_number: "TASK-2024-003",
        capa: 103,
        capa_info: {
            id: 103,
            capa_number: "CAPA-2024-003",
            description: "Training documentation update",
        },
        task_type: "CORRECTIVE",
        task_type_display: "Corrective Action",
        description: "Review and approve updated training materials",
        assigned_to: 1,
        assigned_to_info: {
            id: 1,
            username: "jsmith",
            full_name: "John Smith",
        },
        completion_mode: "SINGLE",
        completion_mode_display: "Single Approver",
        due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 3 days from now
        status: "PENDING",
        status_display: "Pending",
        is_overdue: false,
        requires_signature: false, // Documentation review task
        documents_info: {
            count: 1,
            items: [
                { id: 1003, file_name: "Training_Material_Draft_v2.docx", file_url: "/media/docs/training.docx", upload_date: "2024-12-08T09:00:00Z" },
            ],
        },
        created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    },
];

const MOCK_APPROVALS: PendingApproval[] = [
    {
        id: 201,
        approval_number: "APR-2024-001",
        approval_type: "CAPA_APPROVAL",
        approval_type_display: "CAPA Approval",
        status: "PENDING",
        status_display: "Pending",
        content_type: 15,
        object_id: 104,
        content_object_info: {
            type: "capa",
            id: 104,
            str: "CAPA-2024-004: Equipment calibration schedule review",
        },
        requested_by: 2,
        requested_by_info: {
            id: 2,
            username: "mjones",
            full_name: "Mary Jones",
        },
        requested_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        due_date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Yesterday (overdue)
        reason: "CAPA closure requires Quality Manager approval",
    },
    {
        id: 202,
        approval_number: "APR-2024-002",
        approval_type: "DOCUMENT_APPROVAL",
        approval_type_display: "Document Approval",
        status: "PENDING",
        status_display: "Pending",
        content_type: 10,
        object_id: 501,
        content_object_info: {
            type: "documents",
            id: 501,
            str: "WI-MFG-042 Rev C: Machining Work Instructions",
        },
        requested_by: 3,
        requested_by_info: {
            id: 3,
            username: "bwilson",
            full_name: "Bob Wilson",
        },
        requested_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        due_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 2 days from now
        reason: "Document revision requires review and approval",
    },
    {
        id: 203,
        approval_number: "APR-2024-003",
        approval_type: "CAPA_APPROVAL",
        approval_type_display: "CAPA Approval",
        status: "PENDING",
        status_display: "Pending",
        content_type: 15,
        object_id: 105,
        content_object_info: {
            type: "capa",
            id: 105,
            str: "CAPA-2024-005: Supplier quality improvement initiative",
        },
        requested_by: 4,
        requested_by_info: {
            id: 4,
            username: "sjohnson",
            full_name: "Sarah Johnson",
        },
        requested_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        due_date: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 10 days from now
        reason: "CAPA implementation plan approval",
    },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function InboxPage() {
    const { data: tasksData, isLoading: tasksLoading, error: tasksError } = useMyCapaTasks();
    const { data: approvalsData, isLoading: approvalsLoading, error: approvalsError } = useMyPendingApprovals();

    // Use mock data or real API data based on flag
    const isLoading = USE_MOCK_DATA ? false : (tasksLoading || approvalsLoading);
    const hasError = USE_MOCK_DATA ? false : (tasksError || approvalsError);

    // Transform data to InboxItems
    const rawTasks = USE_MOCK_DATA ? MOCK_TASKS : (tasksData || []);
    const rawApprovals = USE_MOCK_DATA ? MOCK_APPROVALS : (approvalsData || []);

    const tasks = rawTasks.map(transformCapaTask);
    const approvals = rawApprovals.map(transformApproval);
    const items = [...tasks, ...approvals];

    const grouped = groupByUrgency(items);

    const overdueCount = grouped.overdue.length;
    const totalCount = items.length;
    const capaTaskCount = tasks.length;
    const approvalCount = approvals.length;

    if (hasError) {
        return (
            <div className="container mx-auto p-6 max-w-4xl">
                <div className="text-center py-12">
                    <p className="text-destructive">Failed to load inbox items</p>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold">Inbox</h1>
                <p className="text-muted-foreground">
                    {isLoading
                        ? "Loading..."
                        : totalCount === 0
                            ? "You're all caught up!"
                            : overdueCount > 0
                                ? `${overdueCount} overdue, ${totalCount} total items`
                                : `${totalCount} item${totalCount !== 1 ? "s" : ""} requiring attention`
                    }
                </p>
            </div>

            {/* Tabs for filtering */}
            <Tabs defaultValue="all" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="all" className="gap-2">
                        All
                        {totalCount > 0 && <Badge variant="secondary">{totalCount}</Badge>}
                    </TabsTrigger>
                    <TabsTrigger value="tasks" className="gap-2">
                        <ClipboardList className="h-4 w-4" />
                        Tasks
                        {capaTaskCount > 0 && <Badge variant="secondary">{capaTaskCount}</Badge>}
                    </TabsTrigger>
                    <TabsTrigger value="approvals" className="gap-2">
                        <FileSignature className="h-4 w-4" />
                        Approvals
                        {approvalCount > 0 && <Badge variant="secondary">{approvalCount}</Badge>}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-4">
                    {isLoading ? (
                        <LoadingSkeleton />
                    ) : totalCount === 0 ? (
                        <EmptyState />
                    ) : (
                        <>
                            <UrgencySection urgency="overdue" items={grouped.overdue} />
                            <UrgencySection urgency="due_today" items={grouped.due_today} />
                            <UrgencySection urgency="due_this_week" items={grouped.due_this_week} />
                            <UrgencySection urgency="upcoming" items={grouped.upcoming} defaultOpen={false} />
                        </>
                    )}
                </TabsContent>

                <TabsContent value="tasks" className="space-y-4">
                    {isLoading ? (
                        <LoadingSkeleton />
                    ) : capaTaskCount === 0 ? (
                        <EmptyState />
                    ) : (
                        <>
                            <UrgencySection urgency="overdue" items={grouped.overdue.filter(i => i.type === "capa_task")} />
                            <UrgencySection urgency="due_today" items={grouped.due_today.filter(i => i.type === "capa_task")} />
                            <UrgencySection urgency="due_this_week" items={grouped.due_this_week.filter(i => i.type === "capa_task")} />
                            <UrgencySection urgency="upcoming" items={grouped.upcoming.filter(i => i.type === "capa_task")} defaultOpen={false} />
                        </>
                    )}
                </TabsContent>

                <TabsContent value="approvals" className="space-y-4">
                    {isLoading ? (
                        <LoadingSkeleton />
                    ) : approvalCount === 0 ? (
                        <EmptyState />
                    ) : (
                        <>
                            <UrgencySection urgency="overdue" items={grouped.overdue.filter(i => i.type === "approval")} />
                            <UrgencySection urgency="due_today" items={grouped.due_today.filter(i => i.type === "approval")} />
                            <UrgencySection urgency="due_this_week" items={grouped.due_this_week.filter(i => i.type === "approval")} />
                            <UrgencySection urgency="upcoming" items={grouped.upcoming.filter(i => i.type === "approval")} defaultOpen={false} />
                        </>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
