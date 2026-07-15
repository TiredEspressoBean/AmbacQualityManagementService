import { useParams, Link } from "@tanstack/react-router";
import { useRetrieveUser } from "@/hooks/useRetrieveUser";
import { useTrainingRecords } from "@/hooks/useTrainingRecords";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { ArrowLeft, User as UserIcon, GraduationCap, Pencil } from "lucide-react";
import { ReportButton } from "@/components/reports/ReportButton";

export function UserDetailPage() {
    const { id } = useParams({ from: "/admin/users/$id" });
    const userId = Number(id);

    const { data: user, isLoading, error } = useRetrieveUser(
        { params: { id: userId } },
        { enabled: Number.isFinite(userId) },
    );

    const { data: trainingData, isLoading: isLoadingTraining } = useTrainingRecords({ user: userId });
    const trainingRecords = trainingData?.results ?? [];

    if (isLoading) {
        return (
            <div className="container mx-auto p-6 space-y-6">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    if (error || !user) {
        return (
            <div className="container mx-auto p-6">
                <Card className="border-destructive">
                    <CardHeader>
                        <CardTitle className="text-destructive">Error Loading User</CardTitle>
                        <CardDescription>
                            Unable to load user #{id}. They may not exist or you may not have permission to view them.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button asChild variant="outline">
                            <Link to="/admin/users">
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back to Users
                            </Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const groups = (user.groups ?? []) as { id?: number; name?: string }[];

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <Button asChild variant="ghost" size="sm">
                            <Link to="/admin/users">
                                <ArrowLeft className="h-4 w-4 mr-1" />
                                Back
                            </Link>
                        </Button>
                    </div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <UserIcon className="h-6 w-6 text-muted-foreground" />
                        {user.full_name || user.username}
                        {user.is_active ? (
                            <Badge variant="outline" className="text-green-600 border-green-600">
                                Active
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-red-600 border-red-600">
                                Inactive
                            </Badge>
                        )}
                        {user.is_staff && <Badge variant="secondary">Staff</Badge>}
                    </h1>
                    <p className="text-muted-foreground">@{user.username}</p>
                </div>

                <div className="flex items-center gap-2">
                    <ReportButton
                        reportType="training_record"
                        label="Training Record"
                        params={{ user_id: userId }}
                    />
                </div>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="profile" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="profile" className="gap-2">
                        <UserIcon className="h-4 w-4" />
                        Profile
                    </TabsTrigger>
                    <TabsTrigger value="training" className="gap-2">
                        <GraduationCap className="h-4 w-4" />
                        Training
                        {trainingRecords.length > 0 && (
                            <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                                {trainingRecords.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                {/* Profile Tab */}
                <TabsContent value="profile">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>Account Information</CardTitle>
                                    <CardDescription>Account details and membership</CardDescription>
                                </div>
                                <Button asChild variant="outline" size="sm">
                                    <Link to="/UserForm/edit/$id" params={{ id: String(userId) }}>
                                        <Pencil className="h-4 w-4 mr-2" />
                                        Edit profile
                                    </Link>
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <dl className="space-y-3">
                                <div className="flex items-center justify-between py-2 border-b">
                                    <dt className="text-sm font-medium text-muted-foreground">Email</dt>
                                    <dd className="text-sm font-medium">{user.email || "—"}</dd>
                                </div>
                                <div className="flex items-center justify-between py-2 border-b">
                                    <dt className="text-sm font-medium text-muted-foreground">Company</dt>
                                    <dd className="text-sm font-medium">
                                        {user.parent_company?.name || "No company assigned"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between py-2 border-b">
                                    <dt className="text-sm font-medium text-muted-foreground">User type</dt>
                                    <dd className="text-sm font-medium">
                                        {user.user_type_display || user.user_type || "—"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between py-2 border-b">
                                    <dt className="text-sm font-medium text-muted-foreground">Member since</dt>
                                    <dd className="text-sm font-medium">
                                        {user.date_joined
                                            ? new Date(user.date_joined).toLocaleDateString()
                                            : "—"}
                                    </dd>
                                </div>
                                <div className="flex items-start justify-between py-2">
                                    <dt className="text-sm font-medium text-muted-foreground">Groups</dt>
                                    <dd className="flex flex-wrap gap-2 justify-end max-w-[70%]">
                                        {groups.length === 0 ? (
                                            <span className="text-sm text-muted-foreground">—</span>
                                        ) : (
                                            groups.map((group, i) => (
                                                <Badge key={group.id ?? i} variant="outline">
                                                    {group.name ?? "—"}
                                                </Badge>
                                            ))
                                        )}
                                    </dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Training Tab */}
                <TabsContent value="training">
                    <Card>
                        <CardHeader>
                            <CardTitle>Training Records</CardTitle>
                            <CardDescription>
                                Training completed by {user.full_name || user.username}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Training</TableHead>
                                        <TableHead>Completed</TableHead>
                                        <TableHead>Expires</TableHead>
                                        <TableHead>Status</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {isLoadingTraining ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className="text-center py-8">
                                                <Skeleton className="h-5 w-40 mx-auto" />
                                            </TableCell>
                                        </TableRow>
                                    ) : trainingRecords.length === 0 ? (
                                        <TableRow>
                                            <TableCell
                                                colSpan={4}
                                                className="text-center py-8 text-muted-foreground"
                                            >
                                                No training records for this user.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        trainingRecords.map((record) => {
                                            const typeInfo = record.training_type_info as
                                                | { name?: string }
                                                | null
                                                | undefined;
                                            return (
                                                <TableRow key={record.id}>
                                                    <TableCell className="font-medium">
                                                        {typeInfo?.name || "—"}
                                                    </TableCell>
                                                    <TableCell>
                                                        {record.completed_date
                                                            ? new Date(record.completed_date).toLocaleDateString()
                                                            : "—"}
                                                    </TableCell>
                                                    <TableCell>
                                                        {record.expires_date ? (
                                                            <span
                                                                className={
                                                                    record.status === "EXPIRED"
                                                                        ? "text-destructive font-medium"
                                                                        : ""
                                                                }
                                                            >
                                                                {new Date(record.expires_date).toLocaleDateString()}
                                                            </span>
                                                        ) : (
                                                            <span className="text-muted-foreground">Never</span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        <StatusBadge status={record.status?.toUpperCase() || "CURRENT"} />
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
