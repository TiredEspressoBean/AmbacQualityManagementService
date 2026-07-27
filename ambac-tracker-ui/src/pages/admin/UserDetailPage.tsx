import { useState } from "react";
import { useParams, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useRetrieveUser } from "@/hooks/useRetrieveUser";
import { useTrainingRecords } from "@/hooks/useTrainingRecords";
import { api } from "@/lib/api/generated";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { ArrowLeft, Factory, GraduationCap, Pencil, Plus, Star, User as UserIcon, X } from "lucide-react";
import { ReportButton } from "@/components/reports/ReportButton";

type Kind = "PRODUCTION" | "INSPECTION" | "RECEIVING" | "OSP";
const KIND_TONE: Record<Kind, string> = {
    PRODUCTION: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
    INSPECTION: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200",
    RECEIVING: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200",
    OSP: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200",
};

function WorkCentersTab({ userId }: { userId: number }) {
    const qc = useQueryClient();
    const [addWcId, setAddWcId] = useState<string>("");

    const membersKey = ["userwc-memberships", userId] as const;
    const { data: page, isLoading } = useQuery({
        queryKey: membersKey,
        queryFn: () => api.api_UserWorkCenterMemberships_list({
            queries: { user: userId, limit: 100 },
        } as never),
    });
    // eslint-disable-next-line local/no-as-any -- generated union is loose; we only read the fields we typed on the serializer
    const memberships = ((page?.results ?? []) as any[]);

    const { data: wcPage } = useQuery({
        queryKey: ["work-centers", "for-membership-picker"] as const,
        queryFn: () => api.api_WorkCenters_list({ queries: { limit: 100 } } as never),
    });
    // eslint-disable-next-line local/no-as-any -- same as above
    const workCenters = ((wcPage?.results ?? []) as any[]);
    const memberWcIds = new Set(memberships.map((m) => m.work_center));
    const availableWcs = workCenters.filter((wc) => !memberWcIds.has(wc.id));

    const addMut = useMutation({
        mutationFn: (wcId: string) => api.api_UserWorkCenterMemberships_create({
            user: userId, work_center: wcId, is_primary: false,
        } as never),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: membersKey });
            setAddWcId("");
            toast.success("Added.");
        },
        onError: (e) => toast.error(`Couldn't add: ${(e as Error).message}`),
    });
    const removeMut = useMutation({
        mutationFn: (id: string) => api.api_UserWorkCenterMemberships_destroy(undefined as never, { params: { id } }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: membersKey });
            toast.success("Removed.");
        },
        onError: (e) => toast.error(`Couldn't remove: ${(e as Error).message}`),
    });
    const setPrimaryMut = useMutation({
        mutationFn: (id: string) => api.api_UserWorkCenterMemberships_set_primary_create(
            undefined as never, { params: { id } },
        ),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: membersKey });
            toast.success("Primary station set.");
        },
        onError: (e) => toast.error(`Couldn't set primary: ${(e as Error).message}`),
    });

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>Work Center Memberships</CardTitle>
                        <CardDescription>
                            The stations this user is eligible to work at. The operator home defaults to
                            the primary station. See Documents/WORK_CENTER_DESIGN.md.
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Add row */}
                <div className="flex items-center gap-2">
                    <Select value={addWcId} onValueChange={setAddWcId} disabled={availableWcs.length === 0}>
                        <SelectTrigger className="max-w-sm">
                            <SelectValue placeholder={
                                availableWcs.length === 0
                                    ? "User is a member of every work center"
                                    : "Add a work center…"
                            } />
                        </SelectTrigger>
                        <SelectContent>
                            {availableWcs.map((wc) => (
                                <SelectItem key={wc.id} value={wc.id}>
                                    {wc.code} — {wc.name}
                                    <span className="ml-2 text-xs text-muted-foreground">{wc.kind}</span>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Button
                        onClick={() => addWcId && addMut.mutate(addWcId)}
                        disabled={!addWcId || addMut.isPending}
                    >
                        <Plus className="mr-1 h-4 w-4" /> Add
                    </Button>
                </div>

                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Code</TableHead>
                            <TableHead>Work Center</TableHead>
                            <TableHead>Kind</TableHead>
                            <TableHead>Primary</TableHead>
                            <TableHead className="w-32 text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading && (
                            <TableRow>
                                <TableCell colSpan={5} className="py-6 text-center text-muted-foreground">Loading…</TableCell>
                            </TableRow>
                        )}
                        {!isLoading && memberships.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={5} className="py-6 text-center text-muted-foreground">
                                    Not a member of any work center yet.
                                </TableCell>
                            </TableRow>
                        )}
                        {memberships.map((m) => (
                            <TableRow key={m.id}>
                                <TableCell className="font-mono text-xs">{m.work_center_code}</TableCell>
                                <TableCell className="font-medium">{m.work_center_name}</TableCell>
                                <TableCell>
                                    {m.work_center_kind && (
                                        <Badge className={KIND_TONE[m.work_center_kind as Kind] ?? ""}>
                                            {m.work_center_kind}
                                        </Badge>
                                    )}
                                </TableCell>
                                <TableCell>
                                    {m.is_primary ? (
                                        <Badge className="gap-1 bg-amber-500 text-white hover:bg-amber-500">
                                            <Star className="h-3 w-3" /> Primary
                                        </Badge>
                                    ) : (
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            className="h-7 px-2 text-xs text-muted-foreground"
                                            disabled={setPrimaryMut.isPending}
                                            onClick={() => setPrimaryMut.mutate(m.id)}
                                        >
                                            Set primary
                                        </Button>
                                    )}
                                </TableCell>
                                <TableCell className="text-right">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-7 px-2 text-xs text-muted-foreground"
                                        disabled={removeMut.isPending}
                                        onClick={() => removeMut.mutate(m.id)}
                                    >
                                        <X className="mr-1 h-3.5 w-3.5" /> Remove
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}

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
                    <TabsTrigger value="work-centers" className="gap-2">
                        <Factory className="h-4 w-4" />
                        Work Centers
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
                                {/* Internal staff belong to the tenant (their org); only external
                                    portal users carry a customer/external company. Showing an empty
                                    "Company" for staff is misleading — branch on user_type. */}
                                {user.user_type === "PORTAL" ? (
                                    <div className="flex items-center justify-between py-2 border-b">
                                        <dt className="text-sm font-medium text-muted-foreground">Company</dt>
                                        <dd className="text-sm font-medium">
                                            {user.parent_company?.name || "—"}
                                        </dd>
                                    </div>
                                ) : (
                                    <div className="flex items-center justify-between py-2 border-b">
                                        <dt className="text-sm font-medium text-muted-foreground">Organization</dt>
                                        <dd className="text-sm font-medium">
                                            {(user.tenant as { name?: string } | null | undefined)?.name || "—"}
                                        </dd>
                                    </div>
                                )}
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

                {/* Work Centers Tab — station eligibility. See Documents/WORK_CENTER_DESIGN.md. */}
                <TabsContent value="work-centers">
                    <WorkCentersTab userId={userId} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
