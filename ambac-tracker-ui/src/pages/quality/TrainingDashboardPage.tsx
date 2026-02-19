import { Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { GraduationCap, AlertTriangle, CheckCircle2, Clock, Loader2, Users } from "lucide-react"
import { useTrainingStats } from "@/hooks/useTrainingStats"
import { useExpiringTraining } from "@/hooks/useExpiringTraining"
import { useMyTraining } from "@/hooks/useMyTraining"
import { StatusBadge } from "@/components/ui/status-badge"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api/generated"
import type { QueryClient } from "@tanstack/react-query"

// Prefetch function for route loader
export const prefetchTrainingDashboard = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["training-records", "stats"],
        queryFn: () => api.api_TrainingRecords_stats_retrieve(),
    });
    queryClient.prefetchQuery({
        queryKey: ["training-records", "expiring-soon", {}],
        queryFn: () => api.api_TrainingRecords_expiring_soon_list(),
    });
    queryClient.prefetchQuery({
        queryKey: ["training-records", "my-training"],
        queryFn: () => api.api_TrainingRecords_my_training_list(),
    });
};

export function TrainingDashboardPage() {
    const { data: stats, isLoading: statsLoading } = useTrainingStats()
    const { data: expiringData, isLoading: expiringLoading } = useExpiringTraining()
    const { data: myTrainingData, isLoading: myTrainingLoading } = useMyTraining()

    const expiringSoon = expiringData?.results ?? expiringData ?? []
    const myTraining = myTrainingData?.results ?? myTrainingData ?? []

    return (
        <div className="container mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Training Dashboard</h1>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Records</CardTitle>
                        <GraduationCap className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.total_records ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Training completions</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Current</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.current ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Valid training</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Expiring Soon</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-yellow-600">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.expiring_soon ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Within 30 days</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Expired</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-destructive" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-destructive">
                            {statsLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : (stats?.expired ?? 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Needs renewal</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>Training management tasks</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Link
                            to="/quality/training/records"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">View All Training Records</div>
                            <div className="text-sm text-muted-foreground">Browse and manage training completions</div>
                        </Link>
                        <Link
                            to="/quality/training/types"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Manage Training Types</div>
                            <div className="text-sm text-muted-foreground">Configure training categories</div>
                        </Link>
                        <Link
                            to="/TrainingRecordForm/new"
                            className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                        >
                            <div className="font-medium">Record New Training</div>
                            <div className="text-sm text-muted-foreground">Add a training completion</div>
                        </Link>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <Clock className="h-5 w-5" />
                                    Expiring Soon
                                </CardTitle>
                                <CardDescription>Training expiring within 30 days</CardDescription>
                            </div>
                            {Array.isArray(expiringSoon) && expiringSoon.length > 0 && (
                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    {expiringSoon.length}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {expiringLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !Array.isArray(expiringSoon) || expiringSoon.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No training expiring soon</p>
                        ) : (
                            <div className="space-y-2">
                                {expiringSoon.slice(0, 5).map((record: any) => (
                                    <div
                                        key={record.id}
                                        className="p-2 rounded-lg border"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {record.user_info?.full_name || record.user_info?.username}
                                            </span>
                                            <StatusBadge status="EXPIRING_SOON" size="sm" />
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {record.training_type_info?.name}
                                            {record.expires_date && (
                                                <span className="ml-2">
                                                    Expires: {new Date(record.expires_date).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {expiringSoon.length > 5 && (
                                    <Link
                                        to="/quality/training/records"
                                        search={{ status: 'expiring_soon' }}
                                        className="block text-xs text-muted-foreground text-center pt-2 hover:underline"
                                    >
                                        +{expiringSoon.length - 5} more expiring
                                    </Link>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Users className="h-5 w-5" />
                            My Training
                        </CardTitle>
                        <CardDescription>Your training records</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {myTrainingLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        ) : !Array.isArray(myTraining) || myTraining.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No training records</p>
                        ) : (
                            <div className="space-y-2">
                                {myTraining.slice(0, 5).map((record: any) => (
                                    <div
                                        key={record.id}
                                        className="p-2 rounded-lg border"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm truncate">
                                                {record.training_type_info?.name}
                                            </span>
                                            <StatusBadge
                                                status={record.status?.toUpperCase() || 'CURRENT'}
                                                size="sm"
                                            />
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                            Completed: {new Date(record.completed_date).toLocaleDateString()}
                                            {record.expires_date && (
                                                <span className="ml-2">
                                                    | Expires: {new Date(record.expires_date).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {myTraining.length > 5 && (
                                    <p className="text-xs text-muted-foreground text-center pt-2">
                                        +{myTraining.length - 5} more records
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
