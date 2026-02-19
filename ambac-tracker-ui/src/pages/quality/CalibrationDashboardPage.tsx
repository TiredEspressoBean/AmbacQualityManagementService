import { Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Gauge, AlertTriangle, CheckCircle2, Clock, Loader2, Percent } from "lucide-react"
import { useCalibrationStats } from "@/hooks/useCalibrationStats"
import { useCalibrationsDueSoon } from "@/hooks/useCalibrationsDueSoon"
import { useCalibrationsOverdue } from "@/hooks/useCalibrationsOverdue"
import { StatusBadge } from "@/components/ui/status-badge"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api/generated"
import type { QueryClient } from "@tanstack/react-query"

// Prefetch function for route loader
export const prefetchCalibrationDashboard = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["calibration-records", "stats"],
        queryFn: () => api.api_CalibrationRecords_stats_retrieve(),
    });
    queryClient.prefetchQuery({
        queryKey: ["calibration-records", "due-soon", {}],
        queryFn: () => api.api_CalibrationRecords_due_soon_list(),
    });
    queryClient.prefetchQuery({
        queryKey: ["calibration-records", "overdue"],
        queryFn: () => api.api_CalibrationRecords_overdue_list(),
    });
};

export function CalibrationDashboardPage() {
    const { data: stats, isLoading: statsLoading } = useCalibrationStats()
    const { data: dueSoonData, isLoading: dueSoonLoading } = useCalibrationsDueSoon()
    const { data: overdueData, isLoading: overdueLoading } = useCalibrationsOverdue()

    const dueSoon = dueSoonData?.results ?? dueSoonData ?? []
    const overdue = overdueData?.results ?? overdueData ?? []

    return (
        <div className="container mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Calibration Dashboard</h1>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Equipment</CardTitle>
                        <Gauge className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.total_equipment ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">With calibration records</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Current</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.current_calibrations ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">In calibration</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Due Soon</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-yellow-600">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.due_soon ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Within 30 days</p>
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
                        <p className="text-xs text-muted-foreground">Past due</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Compliance</CardTitle>
                        <Percent className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : `${stats?.compliance_rate ?? 0}%`}
                        </div>
                        <p className="text-xs text-muted-foreground">In compliance</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>Calibration management tasks</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Link
                            to="/quality/calibrations/records"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">View All Calibration Records</div>
                            <div className="text-sm text-muted-foreground">Browse calibration history</div>
                        </Link>
                        <Link
                            to="/CalibrationRecordForm/new"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Record New Calibration</div>
                            <div className="text-sm text-muted-foreground">Add a calibration event</div>
                        </Link>
                        <Link
                            to="/editor/equipment"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Manage Equipment</div>
                            <div className="text-sm text-muted-foreground">View and edit equipment</div>
                        </Link>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <Clock className="h-5 w-5" />
                                    Due Soon
                                </CardTitle>
                                <CardDescription>Calibrations due within 30 days</CardDescription>
                            </div>
                            {Array.isArray(dueSoon) && dueSoon.length > 0 && (
                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    {dueSoon.length}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {dueSoonLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !Array.isArray(dueSoon) || dueSoon.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No calibrations due soon</p>
                        ) : (
                            <div className="space-y-2">
                                {dueSoon.slice(0, 5).map((record: any) => (
                                    <div
                                        key={record.id}
                                        className="p-2 rounded-lg border"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {record.equipment_info?.name}
                                            </span>
                                            <StatusBadge status="DUE_SOON" size="sm" />
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {record.equipment_info?.equipment_type}
                                            {record.due_date && (
                                                <span className="ml-2">
                                                    Due: {new Date(record.due_date).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {dueSoon.length > 5 && (
                                    <Link
                                        to="/quality/calibrations/records"
                                        search={{ status: 'due_soon' }}
                                        className="block text-xs text-muted-foreground text-center pt-2 hover:underline"
                                    >
                                        +{dueSoon.length - 5} more due soon
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <AlertTriangle className="h-5 w-5 text-destructive" />
                                    Overdue
                                </CardTitle>
                                <CardDescription>Equipment needing immediate attention</CardDescription>
                            </div>
                            {Array.isArray(overdue) && overdue.length > 0 && (
                                <Badge variant="destructive">
                                    {overdue.length}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {overdueLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !Array.isArray(overdue) || overdue.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No overdue calibrations</p>
                        ) : (
                            <div className="space-y-2">
                                {overdue.slice(0, 5).map((record: any) => (
                                    <div
                                        key={record.id}
                                        className="p-2 rounded-lg border border-destructive/50"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {record.equipment_info?.name}
                                            </span>
                                            <StatusBadge status="OVERDUE" size="sm" />
                                        </div>
                                        <div className="text-xs text-destructive mt-1">
                                            {record.equipment_info?.equipment_type}
                                            {record.days_overdue && (
                                                <span className="ml-2 font-medium">
                                                    {record.days_overdue} days overdue
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {overdue.length > 5 && (
                                    <Link
                                        to="/quality/calibrations/records"
                                        search={{ status: 'overdue' }}
                                        className="block text-xs text-destructive text-center pt-2 hover:underline"
                                    >
                                        +{overdue.length - 5} more overdue
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
