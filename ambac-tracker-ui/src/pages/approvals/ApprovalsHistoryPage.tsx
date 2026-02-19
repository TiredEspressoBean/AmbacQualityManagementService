import { useState, useMemo } from "react"
import { Link, useSearch } from "@tanstack/react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    ArrowLeft,
    Search,
    Loader2,
    Filter,
    X,
    ChevronLeft,
    ChevronRight,
} from "lucide-react"
import { useApprovalRequests } from "@/hooks/useApprovalRequests"
import { useAuthUser } from "@/hooks/useAuthUser"
import { schemas } from "@/lib/api/generated"
import { api } from "@/lib/api/generated"
import type { QueryClient } from "@tanstack/react-query"

// Prefetch function for route loader
export const prefetchApprovalsHistory = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["approvals", "list", { ordering: "-requested_at", limit: 50, offset: 0 }],
        queryFn: () => api.api_ApprovalRequests_list({
            queries: { ordering: "-requested_at", limit: 50 }
        }),
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
            return `/details/${contentType}/${objectId}`;
    }
}

const APPROVAL_TYPES = schemas.ApprovalTypeEnum.options;
const APPROVAL_STATUSES = schemas.ApprovalStatusEnum.options;

const PAGE_SIZE = 20;

export function ApprovalsHistoryPage() {
    const { data: user } = useAuthUser()
    const searchParams = useSearch({ strict: false }) as Record<string, any>

    // Filter state
    const [search, setSearch] = useState("")
    const [statusFilter, setStatusFilter] = useState<string>(searchParams?.status || "all")
    const [typeFilter, setTypeFilter] = useState<string>("all")
    const [showMyRequestsOnly, setShowMyRequestsOnly] = useState(searchParams?.myRequests === true)
    const [page, setPage] = useState(0)

    // Build query filters
    const queryFilters = useMemo(() => ({
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        approval_type: typeFilter !== "all" ? typeFilter : undefined,
        requested_by: showMyRequestsOnly && user?.id ? user.id : undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        ordering: "-requested_at",
    }), [search, statusFilter, typeFilter, showMyRequestsOnly, user?.id, page])

    const { data, isLoading } = useApprovalRequests(queryFilters)

    const approvals = data?.results ?? []
    const totalCount = data?.count ?? 0
    const totalPages = Math.ceil(totalCount / PAGE_SIZE)

    const clearFilters = () => {
        setSearch("")
        setStatusFilter("all")
        setTypeFilter("all")
        setShowMyRequestsOnly(false)
        setPage(0)
    }

    const hasActiveFilters = search || statusFilter !== "all" || typeFilter !== "all" || showMyRequestsOnly

    return (
        <div className="container mx-auto p-6">
            <div className="flex items-center gap-4 mb-6">
                <Link to="/approvals">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <h1 className="text-2xl font-bold">Approval History</h1>
            </div>

            {/* Filters */}
            <Card className="mb-6">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Filter className="h-4 w-4" />
                            Filters
                        </CardTitle>
                        {hasActiveFilters && (
                            <Button variant="ghost" size="sm" onClick={clearFilters}>
                                <X className="h-4 w-4 mr-1" />
                                Clear
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                        <div className="space-y-2">
                            <Label>Search</Label>
                            <div className="relative">
                                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search approvals..."
                                    value={search}
                                    onChange={(e) => {
                                        setSearch(e.target.value)
                                        setPage(0)
                                    }}
                                    className="pl-8"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Status</Label>
                            <Select
                                value={statusFilter}
                                onValueChange={(v) => {
                                    setStatusFilter(v)
                                    setPage(0)
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="All statuses" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Statuses</SelectItem>
                                    {APPROVAL_STATUSES.map((status) => (
                                        <SelectItem key={status} value={status}>
                                            {status.replace(/_/g, " ")}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Type</Label>
                            <Select
                                value={typeFilter}
                                onValueChange={(v) => {
                                    setTypeFilter(v)
                                    setPage(0)
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="All types" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Types</SelectItem>
                                    {APPROVAL_TYPES.map((type) => (
                                        <SelectItem key={type} value={type}>
                                            {type.replace(/_/g, " ")}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Scope</Label>
                            <Select
                                value={showMyRequestsOnly ? "mine" : "all"}
                                onValueChange={(v) => {
                                    setShowMyRequestsOnly(v === "mine")
                                    setPage(0)
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Approvals</SelectItem>
                                    <SelectItem value="mine">My Requests Only</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-end">
                            <div className="text-sm text-muted-foreground">
                                {totalCount} result{totalCount !== 1 ? "s" : ""}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Results Table */}
            <Card>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : approvals.length === 0 ? (
                        <div className="text-center py-12">
                            <p className="text-muted-foreground">No approvals found</p>
                            {hasActiveFilters && (
                                <Button variant="link" onClick={clearFilters} className="mt-2">
                                    Clear filters
                                </Button>
                            )}
                        </div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Item</TableHead>
                                        <TableHead>Type</TableHead>
                                        <TableHead>Requested By</TableHead>
                                        <TableHead>Requested</TableHead>
                                        <TableHead>Due Date</TableHead>
                                        <TableHead>Status</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {approvals.map((approval) => {
                                        const isOverdue = approval.due_date &&
                                            approval.status === "PENDING" &&
                                            new Date(approval.due_date) < new Date();

                                        return (
                                            <TableRow key={approval.id} className="cursor-pointer hover:bg-accent/50">
                                                <TableCell>
                                                    <Link
                                                        to={getApprovalDetailLink(approval)}
                                                        className="font-medium hover:underline"
                                                    >
                                                        {approval.content_object_info?.str || `#${approval.object_id}`}
                                                    </Link>
                                                    {approval.approval_number && (
                                                        <div className="text-xs text-muted-foreground">
                                                            {approval.approval_number}
                                                        </div>
                                                    )}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="outline" className="text-xs">
                                                        {approval.approval_type_display || approval.approval_type?.replace(/_/g, " ")}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm">
                                                        {approval.requested_by_info?.full_name ||
                                                            approval.requested_by_info?.username ||
                                                            "Unknown"}
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm">
                                                        {new Date(approval.requested_at).toLocaleDateString()}
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">
                                                        {new Date(approval.requested_at).toLocaleTimeString([], {
                                                            hour: "2-digit",
                                                            minute: "2-digit"
                                                        })}
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    {approval.due_date ? (
                                                        <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                                            {new Date(approval.due_date).toLocaleDateString()}
                                                            {isOverdue && " (Overdue)"}
                                                        </span>
                                                    ) : (
                                                        <span className="text-muted-foreground">-</span>
                                                    )}
                                                </TableCell>
                                                <TableCell>
                                                    <StatusBadge status={approval.status} size="sm" />
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-between px-4 py-3 border-t">
                                    <div className="text-sm text-muted-foreground">
                                        Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setPage(p => Math.max(0, p - 1))}
                                            disabled={page === 0}
                                        >
                                            <ChevronLeft className="h-4 w-4" />
                                            Previous
                                        </Button>
                                        <span className="text-sm text-muted-foreground">
                                            Page {page + 1} of {totalPages}
                                        </span>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                            disabled={page >= totalPages - 1}
                                        >
                                            Next
                                            <ChevronRight className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}

export default ApprovalsHistoryPage
