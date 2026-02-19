import { Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import {
    FileSignature,
    Clock,
    CheckCircle2,
    AlertTriangle,
    Loader2,
    Send,
    ArrowRight,
    ClipboardList,
} from "lucide-react"
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals"
import { useMySubmittedRequests } from "@/hooks/useApprovalRequests"
import { useAuthUser } from "@/hooks/useAuthUser"
import { api } from "@/lib/api/generated"
import type { QueryClient } from "@tanstack/react-query"

// Prefetch function for route loader
export const prefetchApprovalsOverview = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["approvals", "my-pending"],
        queryFn: () => api.api_ApprovalRequests_my_pending_list(),
    });
};

// Helper to get the detail link for an approval based on its type
function getApprovalDetailLink(approval: any): string {
    const contentType = approval.content_object_info?.type?.toLowerCase();
    const objectId = approval.object_id;

    switch (contentType) {
        case "document":
            return `/documents/${objectId}`;
        case "capa":
            return `/quality/capas/${objectId}`;
        case "process":
            return `/process-flow?processId=${objectId}`;
        default:
            // Fallback - try to construct from content type name
            return `/details/${contentType}/${objectId}`;
    }
}

// Helper to format approval type for display
function formatApprovalType(type: string): string {
    return type
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase());
}

export function ApprovalsOverviewPage() {
    const { data: user } = useAuthUser()
    const { data: pendingApprovals, isLoading: pendingLoading } = useMyPendingApprovals()
    const { data: myRequestsData, isLoading: requestsLoading } = useMySubmittedRequests(user?.id)

    const myRequests = myRequestsData?.results ?? []

    // Calculate stats
    const pendingCount = pendingApprovals?.length ?? 0
    const overdueCount = pendingApprovals?.filter(a => {
        if (!a.due_date) return false;
        return new Date(a.due_date) < new Date();
    }).length ?? 0
    const myRequestsPendingCount = myRequests.filter(r => r.status === "PENDING").length
    const myRequestsApprovedCount = myRequests.filter(r => r.status === "APPROVED").length

    // Group pending by type
    const pendingByType = pendingApprovals?.reduce((acc, approval) => {
        const type = approval.approval_type_display || approval.approval_type;
        acc[type] = (acc[type] || 0) + 1;
        return acc;
    }, {} as Record<string, number>) ?? {};

    return (
        <div className="container mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold">Approvals</h1>
                <Link to="/approvals/history">
                    <Button variant="outline">
                        View All History
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                </Link>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Awaiting My Approval</CardTitle>
                        <FileSignature className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {pendingLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : pendingCount}
                        </div>
                        <p className="text-xs text-muted-foreground">Items requiring your action</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Overdue</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-destructive" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-destructive">
                            {pendingLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : overdueCount}
                        </div>
                        <p className="text-xs text-muted-foreground">Past due date</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">My Requests Pending</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {requestsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : myRequestsPendingCount}
                        </div>
                        <p className="text-xs text-muted-foreground">Awaiting others' approval</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Recently Approved</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {requestsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : myRequestsApprovedCount}
                        </div>
                        <p className="text-xs text-muted-foreground">My requests completed</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* My Pending Approvals */}
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <FileSignature className="h-5 w-5" />
                                    Awaiting My Approval
                                </CardTitle>
                                <CardDescription>Items that need your review and decision</CardDescription>
                            </div>
                            {pendingCount > 0 && (
                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    {pendingCount}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {pendingLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : pendingCount === 0 ? (
                            <div className="text-center py-8">
                                <CheckCircle2 className="h-12 w-12 mx-auto text-green-500 mb-2" />
                                <p className="text-muted-foreground">All caught up! No approvals pending.</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {pendingApprovals?.slice(0, 8).map((approval) => {
                                    const isOverdue = approval.due_date && new Date(approval.due_date) < new Date();
                                    return (
                                        <Link
                                            key={approval.id}
                                            to={getApprovalDetailLink(approval)}
                                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="font-medium truncate">
                                                    {approval.content_object_info?.str || `#${approval.object_id}`}
                                                </span>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="outline" className="text-xs">
                                                        {approval.approval_type_display || formatApprovalType(approval.approval_type)}
                                                    </Badge>
                                                    <StatusBadge status="PENDING" size="sm" />
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-between mt-1">
                                                <span className="text-xs text-muted-foreground">
                                                    From {approval.requested_by_info?.full_name || approval.requested_by_info?.username || "Unknown"}
                                                </span>
                                                {approval.due_date && (
                                                    <span className={`text-xs ${isOverdue ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                                                        Due: {new Date(approval.due_date).toLocaleDateString()}
                                                        {isOverdue && " (Overdue)"}
                                                    </span>
                                                )}
                                            </div>
                                        </Link>
                                    );
                                })}
                                {pendingCount > 8 && (
                                    <Link
                                        to="/approvals/history"
                                        search={{ status: "PENDING" }}
                                        className="block text-sm text-center text-primary hover:underline pt-2"
                                    >
                                        View all {pendingCount} pending approvals
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Breakdown by Type */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ClipboardList className="h-5 w-5" />
                            By Type
                        </CardTitle>
                        <CardDescription>Pending approvals breakdown</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {pendingLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : Object.keys(pendingByType).length === 0 ? (
                            <p className="text-sm text-muted-foreground">No pending approvals</p>
                        ) : (
                            <div className="space-y-3">
                                {Object.entries(pendingByType).map(([type, count]) => (
                                    <div key={type} className="flex items-center justify-between">
                                        <span className="text-sm">{type}</span>
                                        <Badge variant="secondary">{count}</Badge>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* My Submitted Requests */}
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <Send className="h-5 w-5" />
                                    My Submitted Requests
                                </CardTitle>
                                <CardDescription>Approvals you've requested from others</CardDescription>
                            </div>
                            {myRequestsPendingCount > 0 && (
                                <Badge variant="secondary">
                                    {myRequestsPendingCount} pending
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {requestsLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : myRequests.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-8">
                                You haven't submitted any approval requests yet.
                            </p>
                        ) : (
                            <div className="space-y-2">
                                {myRequests.slice(0, 5).map((request) => (
                                    <Link
                                        key={request.id}
                                        to={getApprovalDetailLink(request)}
                                        className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium truncate">
                                                {request.content_object_info?.str || `#${request.object_id}`}
                                            </span>
                                            <StatusBadge status={request.status} size="sm" />
                                        </div>
                                        <div className="flex items-center justify-between mt-1">
                                            <span className="text-xs text-muted-foreground">
                                                {request.approval_type_display || formatApprovalType(request.approval_type)}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {new Date(request.requested_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </Link>
                                ))}
                                {myRequests.length > 5 && (
                                    <Link
                                        to="/approvals/history"
                                        search={{ myRequests: true }}
                                        className="block text-sm text-center text-primary hover:underline pt-2"
                                    >
                                        View all {myRequests.length} requests
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Quick Links */}
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Links</CardTitle>
                        <CardDescription>Manage approval system</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Link
                            to="/approvals/history"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Approval History</div>
                            <div className="text-sm text-muted-foreground">View all past approvals</div>
                        </Link>
                        <Link
                            to="/editor/approvalTemplates"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Approval Templates</div>
                            <div className="text-sm text-muted-foreground">Configure approval workflows</div>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}

export default ApprovalsOverviewPage
