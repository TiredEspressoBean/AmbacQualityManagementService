import { useMyCapaTasks } from "@/hooks/useMyCapaTasks";
import { useMyPendingApprovals, type PendingApproval } from "@/hooks/useMyPendingApprovals";
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
    CheckSquare,
    ClipboardList,
    FileSignature,
    Calendar,
    ArrowRight,
    AlertTriangle,
} from "lucide-react";

function TasksLoadingSkeleton() {
    return (
        <div className="space-y-3">
            {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                    </div>
                    <Skeleton className="h-8 w-20" />
                </div>
            ))}
        </div>
    );
}

function EmptyState({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
            <Icon className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground">{title}</h3>
            <p className="text-sm text-muted-foreground/70 mt-1">{description}</p>
        </div>
    );
}

function CapaTasksList() {
    const { data, isLoading, error } = useMyCapaTasks();

    if (isLoading) return <TasksLoadingSkeleton />;
    if (error) return <div className="text-destructive">Error loading tasks</div>;

    const tasks = data || [];

    if (tasks.length === 0) {
        return (
            <EmptyState
                icon={CheckSquare}
                title="No CAPA tasks assigned"
                description="You're all caught up! Tasks will appear here when assigned to you."
            />
        );
    }

    return (
        <div className="space-y-3">
            {tasks.map((task) => {
                const isOverdue = task.due_date && new Date(task.due_date) < new Date();
                return (
                    <Link
                        key={task.id}
                        to="/quality/capas/$id"
                        params={{ id: String(task.capa) }}
                        className="block"
                    >
                        <div className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                <ClipboardList className="h-5 w-5 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium truncate">{task.description || task.task_type_display}</span>
                                    {isOverdue && (
                                        <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                                    )}
                                </div>
                                <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                                    <span>{(task.capa_info as any)?.capa_number || `CAPA #${task.capa}`}</span>
                                    {task.due_date && (
                                        <span className={`flex items-center gap-1 ${isOverdue ? "text-destructive" : ""}`}>
                                            <Calendar className="h-3 w-3" />
                                            {new Date(task.due_date).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <StatusBadge status={task.status} />
                            <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        </div>
                    </Link>
                );
            })}
        </div>
    );
}

function ApprovalsList() {
    const { data, isLoading, error } = useMyPendingApprovals();

    if (isLoading) return <TasksLoadingSkeleton />;
    if (error) return <div className="text-destructive">Error loading approvals</div>;

    const approvals = data || [];

    if (approvals.length === 0) {
        return (
            <EmptyState
                icon={FileSignature}
                title="No pending approvals"
                description="Nothing needs your approval right now."
            />
        );
    }

    return (
        <div className="space-y-3">
            {approvals.map((approval: PendingApproval) => {
                const isOverdue = approval.due_date ? new Date(approval.due_date) < new Date() : false;
                return (
                    <div
                        key={approval.id}
                        className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100">
                            <FileSignature className="h-5 w-5 text-amber-700" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="font-medium truncate">
                                    {approval.approval_type_display}
                                </span>
                                <span className="text-muted-foreground font-mono text-sm">
                                    {approval.approval_number}
                                </span>
                                {isOverdue && (
                                    <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                                )}
                            </div>
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                                {(approval.content_object_info as any)?.str && (
                                    <span>{(approval.content_object_info as any).str}</span>
                                )}
                                {approval.requested_by_info && (
                                    <span>
                                        from {(approval.requested_by_info as any).full_name || (approval.requested_by_info as any).username}
                                    </span>
                                )}
                                {approval.due_date && (
                                    <span className={`flex items-center gap-1 ${isOverdue ? "text-destructive" : ""}`}>
                                        <Calendar className="h-3 w-3" />
                                        {new Date(approval.due_date).toLocaleDateString()}
                                    </span>
                                )}
                            </div>
                        </div>
                        <StatusBadge status={approval.status} />
                        <Button variant="outline" size="sm">
                            Review
                        </Button>
                    </div>
                );
            })}
        </div>
    );
}

export function MyTasksPage() {
    const { data: tasksData } = useMyCapaTasks();
    const { data: approvalsData } = useMyPendingApprovals();

    const taskCount = tasksData?.length || 0;
    const approvalCount = approvalsData?.length || 0;
    const totalCount = taskCount + approvalCount;

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            <div className="mb-6">
                <h1 className="text-2xl font-bold">Inbox</h1>
                <p className="text-muted-foreground">
                    {totalCount > 0
                        ? `You have ${totalCount} item${totalCount !== 1 ? "s" : ""} requiring attention`
                        : "You're all caught up!"}
                </p>
            </div>

            <Tabs defaultValue="all" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="all" className="gap-2">
                        All
                        {totalCount > 0 && (
                            <Badge variant="secondary" className="ml-1">
                                {totalCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="tasks" className="gap-2">
                        <ClipboardList className="h-4 w-4" />
                        CAPA Tasks
                        {taskCount > 0 && (
                            <Badge variant="secondary" className="ml-1">
                                {taskCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="approvals" className="gap-2">
                        <FileSignature className="h-4 w-4" />
                        Approvals
                        {approvalCount > 0 && (
                            <Badge variant="secondary" className="ml-1">
                                {approvalCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-6">
                    {approvalCount > 0 && (
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <FileSignature className="h-5 w-5" />
                                    Pending Approvals
                                </CardTitle>
                                <CardDescription>
                                    Items waiting for your review and approval
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ApprovalsList />
                            </CardContent>
                        </Card>
                    )}

                    {taskCount > 0 && (
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <ClipboardList className="h-5 w-5" />
                                    CAPA Tasks
                                </CardTitle>
                                <CardDescription>
                                    Action items assigned to you from CAPAs
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <CapaTasksList />
                            </CardContent>
                        </Card>
                    )}

                    {totalCount === 0 && (
                        <Card>
                            <CardContent className="pt-6">
                                <EmptyState
                                    icon={CheckSquare}
                                    title="All clear!"
                                    description="You have no pending tasks or approvals."
                                />
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                <TabsContent value="tasks">
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <ClipboardList className="h-5 w-5" />
                                CAPA Tasks
                            </CardTitle>
                            <CardDescription>
                                Action items assigned to you from CAPAs
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <CapaTasksList />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="approvals">
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <FileSignature className="h-5 w-5" />
                                Pending Approvals
                            </CardTitle>
                            <CardDescription>
                                Items waiting for your review and approval
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ApprovalsList />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
