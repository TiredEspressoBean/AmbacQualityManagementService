import { Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import {
    Clock,
    Files,
    FileSignature,
    Upload,
    Loader2,
    FileText,
    FolderOpen,
    AlertTriangle,
} from "lucide-react"
import { useDocumentStats } from "@/hooks/useDocumentStats"
import { useRecentDocuments } from "@/hooks/useRecentDocuments"
import { useDocumentsPendingApproval } from "@/hooks/useDocumentsPendingApproval"

export function DocumentsDashboardPage() {
    const { data: stats, isLoading: statsLoading } = useDocumentStats()
    const { data: recentDocs, isLoading: recentLoading } = useRecentDocuments()
    const { data: pendingApprovals, isLoading: approvalsLoading } = useDocumentsPendingApproval()

    return (
        <div className="container mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Documents</h1>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                        <Files className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.total ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">In the system</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.pending_approval ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Awaiting review</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Needs My Approval</CardTitle>
                        <FileSignature className="h-4 w-4 text-orange-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-orange-600">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.needs_my_approval ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Requiring your action</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">My Uploads</CardTitle>
                        <Upload className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.my_uploads ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Uploaded by you</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Quick Actions */}
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>Common document tasks</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Link
                            to="/documents/list"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="flex items-center gap-2">
                                <FolderOpen className="h-4 w-4" />
                                <div className="font-medium">View All Documents</div>
                            </div>
                            <div className="text-sm text-muted-foreground ml-6">Browse and search documents</div>
                        </Link>
                        <Link
                            to="/DocumentForm/create"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="flex items-center gap-2">
                                <Upload className="h-4 w-4" />
                                <div className="font-medium">Upload Document</div>
                            </div>
                            <div className="text-sm text-muted-foreground ml-6">Add a new document to the system</div>
                        </Link>
                        {(stats?.needs_my_approval ?? 0) > 0 && (
                            <Link
                                to="/documents/list"
                                search={{ needsMyApproval: true }}
                                className="block p-3 rounded-lg border border-orange-200 bg-orange-50 hover:bg-orange-100 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="h-4 w-4 text-orange-600" />
                                    <div className="font-medium text-orange-800">Documents Needing Approval</div>
                                </div>
                                <div className="text-sm text-orange-700 ml-6">
                                    {stats?.needs_my_approval} document(s) require your review
                                </div>
                            </Link>
                        )}
                    </CardContent>
                </Card>

                {/* My Pending Approvals */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <FileSignature className="h-5 w-5" />
                                    Pending My Approval
                                </CardTitle>
                                <CardDescription>Documents requiring your approval</CardDescription>
                            </div>
                            {(pendingApprovals?.length ?? 0) > 0 && (
                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    {pendingApprovals?.length}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {approvalsLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !pendingApprovals?.length ? (
                            <p className="text-sm text-muted-foreground">No approvals pending</p>
                        ) : (
                            <div className="space-y-2">
                                {pendingApprovals.slice(0, 5).map((approval) => (
                                    <Link
                                        key={approval.id}
                                        to="/documents/$id"
                                        params={{ id: String(approval.object_id) }}
                                        className="block p-2 rounded-lg border hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {approval.content_object_display || `Document #${approval.object_id}`}
                                            </span>
                                            <StatusBadge status="PENDING" className="ml-2" />
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {approval.approval_type_display || approval.approval_type}
                                            {approval.due_date && (
                                                <span className={approval.is_overdue ? "text-destructive ml-2" : "ml-2"}>
                                                    Due: {new Date(approval.due_date).toLocaleDateString()}
                                                    {approval.is_overdue && " (Overdue)"}
                                                </span>
                                            )}
                                        </div>
                                    </Link>
                                ))}
                                {pendingApprovals.length > 5 && (
                                    <p className="text-xs text-muted-foreground text-center pt-2">
                                        +{pendingApprovals.length - 5} more
                                    </p>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Recently Updated */}
                <Card>
                    <CardHeader>
                        <CardTitle>Recently Updated</CardTitle>
                        <CardDescription>Latest document activity</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {recentLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !recentDocs?.length ? (
                            <p className="text-sm text-muted-foreground">No recent documents</p>
                        ) : (
                            <div className="space-y-2">
                                {recentDocs.slice(0, 5).map((doc) => (
                                    <Link
                                        key={doc.id}
                                        to="/documents/$id"
                                        params={{ id: String(doc.id) }}
                                        className="block p-2 rounded-lg border hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                            <span className="font-medium text-sm truncate">{doc.file_name}</span>
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1 ml-6">
                                            {doc.uploaded_by_name} &middot; {new Date(doc.updated_at || doc.upload_date).toLocaleDateString()}
                                        </div>
                                    </Link>
                                ))}
                                {recentDocs.length > 5 && (
                                    <Link
                                        to="/documents/list"
                                        className="block text-xs text-center text-primary hover:underline pt-2"
                                    >
                                        View all documents
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Classification Breakdown (optional - only show if we have data) */}
            {stats?.by_classification && Object.keys(stats.by_classification).length > 0 && (
                <Card className="mt-6">
                    <CardHeader>
                        <CardTitle>Documents by Classification</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-4">
                            {Object.entries(stats.by_classification).map(([classification, count]) => (
                                <div key={classification} className="flex items-center gap-2">
                                    <Badge variant="outline" className="capitalize">
                                        {classification}
                                    </Badge>
                                    <span className="text-sm font-medium">{count}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
