import { Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ShieldCheck, ClipboardList, AlertTriangle, CheckCircle2, Loader2, FileSignature } from "lucide-react"
import { useCapaStats } from "@/hooks/useCapaStats"
import { useMyCapaTasks } from "@/hooks/useMyCapaTasks"
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { api } from "@/lib/api/generated"
import type { QueryClient } from "@tanstack/react-query"

// Prefetch function for route loader - uses same query keys as hooks
export const prefetchQualityDashboard = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["capa-stats"],
        queryFn: () => api.api_CAPAs_stats_retrieve(),
    });
    queryClient.prefetchQuery({
        queryKey: ["capa-my-tasks"],
        queryFn: () => api.api_CAPAs_my_tasks_list(),
    });
    queryClient.prefetchQuery({
        queryKey: ["approvals", "my-pending"],
        queryFn: () => api.api_approvals_my_pending_list(),
    });
};

export function QualityDashboardPage() {
    const { data: stats, isLoading: statsLoading } = useCapaStats()
    const { data: myTasksData, isLoading: tasksLoading } = useMyCapaTasks()
    const { data: approvalsData, isLoading: approvalsLoading } = useMyPendingApprovals()

    const myTasks = myTasksData?.results ?? []
    const pendingApprovals = approvalsData?.results ?? []

    // Calculate open CAPAs (open + in_progress)
    const openCapas = (stats?.by_status?.open ?? 0) + (stats?.by_status?.in_progress ?? 0)

    return (
        <div className="container mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Quality Dashboard</h1>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Open CAPAs</CardTitle>
                        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : openCapas}
                        </div>
                        <p className="text-xs text-muted-foreground">Requiring attention</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Overdue</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-destructive" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-destructive">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.overdue ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Past due date</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending Verification</CardTitle>
                        <ClipboardList className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.by_status?.pending_verification ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Awaiting review</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Closed</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.by_status?.closed ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Successfully resolved</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>Common quality tasks</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Link
                            to="/quality/capas"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">View All CAPAs</div>
                            <div className="text-sm text-muted-foreground">Manage corrective and preventive actions</div>
                        </Link>
                        <Link
                            to="/quality/capas/new"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Create New CAPA</div>
                            <div className="text-sm text-muted-foreground">Start a new corrective or preventive action</div>
                        </Link>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <FileSignature className="h-5 w-5" />
                                    My Pending Approvals
                                </CardTitle>
                                <CardDescription>Items requiring your approval</CardDescription>
                            </div>
                            {pendingApprovals.length > 0 && (
                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    {pendingApprovals.length}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {approvalsLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : pendingApprovals.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No approvals pending</p>
                        ) : (
                            <div className="space-y-2">
                                {pendingApprovals.slice(0, 5).map((approval) => (
                                    <Link
                                        key={approval.id}
                                        to="/quality/capas/$id"
                                        params={{ id: String(approval.object_id) }}
                                        className="block p-2 rounded-lg border hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {approval.content_object_display || `#${approval.object_id}`}
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
                                        +{pendingApprovals.length - 5} more approvals
                                    </p>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>My Tasks</CardTitle>
                        <CardDescription>CAPA tasks assigned to you</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {tasksLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : myTasks.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No tasks assigned</p>
                        ) : (
                            <div className="space-y-2">
                                {myTasks.slice(0, 5).map((task) => (
                                    <Link
                                        key={task.id}
                                        to="/quality/capas/$id"
                                        params={{ id: String(task.capa) }}
                                        className="block p-2 rounded-lg border hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">{task.title}</span>
                                            <Badge variant={task.status === 'PENDING' ? 'secondary' : 'outline'} className="ml-2">
                                                {task.status}
                                            </Badge>
                                        </div>
                                        {task.due_date && (
                                            <div className="text-xs text-muted-foreground mt-1">
                                                Due: {new Date(task.due_date).toLocaleDateString()}
                                            </div>
                                        )}
                                    </Link>
                                ))}
                                {myTasks.length > 5 && (
                                    <p className="text-xs text-muted-foreground text-center pt-2">
                                        +{myTasks.length - 5} more tasks
                                    </p>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}