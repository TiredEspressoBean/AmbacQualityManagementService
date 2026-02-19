import { useState, useMemo } from "react";
import { useParams, Link } from "@tanstack/react-router";
import { useTenantGroup } from "@/hooks/useTenantGroup";
import {
    useTenantGroupMembers,
    useAddTenantGroupMember,
    useRemoveTenantGroupMember,
} from "@/hooks/useTenantGroupMembers";
import {
    useAddTenantGroupPermissions,
    useSetTenantGroupPermissions,
} from "@/hooks/useTenantGroupPermissions";
import { useAvailablePermissions, type Permission } from "@/hooks/useAvailablePermissions";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
    ArrowLeft,
    Users,
    Shield,
    Loader2,
    UserPlus,
    UserMinus,
    Search,
    ShieldPlus,
    ShieldMinus,
} from "lucide-react";
import { toast } from "sonner";

// Member type from /api/TenantGroups/:id/members/
type GroupMember = {
    id: string;
    user: number;
    user_email: string;
    user_name: string;
    group: string;
    group_name: string;
    company?: string | null;
    company_name?: string | null;
    facility?: string | null;
    facility_name?: string | null;
    granted_at: string;
    granted_by?: number | null;
    granted_by_name?: string | null;
};

type GroupPermission = {
    codename: string;
    name: string;
    content_type?: string;
};

type ExtendedTenantGroup = {
    id: string;
    name: string;
    description?: string;
    is_custom: boolean;
    permission_count: number;
    member_count: number;
    preset_key: string | null;
    permissions: string[] | GroupPermission[];
    members?: GroupMember[];
};

export function GroupDetailPage() {
    const { id } = useParams({ from: "/editor/groups/$id" });
    const groupId = id;
    const { data: group, isLoading, error } = useTenantGroup(groupId) as {
        data: ExtendedTenantGroup | undefined;
        isLoading: boolean;
        error: Error | null;
    };

    // Fetch members separately - returns array directly
    const { data: membersData, isLoading: membersLoading } = useTenantGroupMembers(groupId);
    const groupMembers: GroupMember[] = membersData || [];

    const { data: usersData } = useRetrieveUsers({ limit: 200, is_active: true });
    const availableUsers = usersData?.results || [];

    const { data: permissionsData } = useAvailablePermissions();
    const allPermissions: Permission[] = (permissionsData as any)?.permissions || [];

    const addMemberMutation = useAddTenantGroupMember(groupId);
    const removeMemberMutation = useRemoveTenantGroupMember(groupId);
    const addPermissionsMutation = useAddTenantGroupPermissions(groupId);
    const setPermissionsMutation = useSetTenantGroupPermissions(groupId);

    // User state
    const [showAddUsersDialog, setShowAddUsersDialog] = useState(false);
    const [selectedUsersToAdd, setSelectedUsersToAdd] = useState<number[]>([]);
    const [selectedUsersToRemove, setSelectedUsersToRemove] = useState<number[]>([]);
    const [userSearchQuery, setUserSearchQuery] = useState("");

    // Permission state
    const [permissionSearchQuery, setPermissionSearchQuery] = useState("");

    // Normalize permissions - could be strings or objects
    const groupPermissions = useMemo(() => {
        if (!group?.permissions) return [];
        return group.permissions.map((p) => {
            if (typeof p === "string") {
                // Try to find full info from allPermissions
                const full = allPermissions.find((ap) => ap.codename === p);
                return full || { codename: p, name: p, content_type: "" };
            }
            return p;
        });
    }, [group?.permissions, allPermissions]);

    // Permissions not yet granted to group
    const groupPermCodenames = useMemo(() => {
        return new Set(groupPermissions.map((p) => p.codename));
    }, [groupPermissions]);

    const availablePermissions = useMemo(() => {
        return allPermissions.filter((p) => !groupPermCodenames.has(p.codename));
    }, [allPermissions, groupPermCodenames]);


    if (isLoading) {
        return (
            <div className="container mx-auto p-6 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    if (error || !group) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center py-12">
                    <h2 className="text-xl font-semibold mb-2">Group Not Found</h2>
                    <p className="text-muted-foreground mb-4">
                        The group you're looking for doesn't exist or you don't have access.
                    </p>
                    <Link to="/editor/groups">
                        <Button variant="outline">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Groups
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    // Filter users not already in group
    const memberUserIds = new Set(groupMembers.map((m) => m.user));
    const usersNotInGroup = availableUsers.filter(
        (user) => !memberUserIds.has(user.id)
    );

    // Filter by search
    const filteredUsersToAdd = usersNotInGroup.filter(
        (user) =>
            user.email?.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
            user.first_name?.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
            user.last_name?.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
            user.username?.toLowerCase().includes(userSearchQuery.toLowerCase())
    );

    const filteredGrantedPermissions = groupPermissions.filter(
        (p) =>
            p.codename.toLowerCase().includes(permissionSearchQuery.toLowerCase()) ||
            p.name.toLowerCase().includes(permissionSearchQuery.toLowerCase())
    );

    const filteredAvailablePermissions = availablePermissions.filter(
        (p) =>
            p.codename.toLowerCase().includes(permissionSearchQuery.toLowerCase()) ||
            p.name.toLowerCase().includes(permissionSearchQuery.toLowerCase())
    );

    const handleAddUsers = async () => {
        if (selectedUsersToAdd.length === 0) return;

        try {
            for (const userId of selectedUsersToAdd) {
                await addMemberMutation.mutateAsync(String(userId));
            }
            toast.success(`Added ${selectedUsersToAdd.length} user(s) to ${group.name}`);
            setSelectedUsersToAdd([]);
            setShowAddUsersDialog(false);
        } catch (err) {
            toast.error("Failed to add users");
        }
    };

    const handleRemoveUsers = async () => {
        if (selectedUsersToRemove.length === 0) return;

        try {
            for (const userId of selectedUsersToRemove) {
                await removeMemberMutation.mutateAsync(String(userId));
            }
            toast.success(`Removed ${selectedUsersToRemove.length} user(s) from ${group.name}`);
            setSelectedUsersToRemove([]);
        } catch (err) {
            toast.error("Failed to remove users");
        }
    };

    const toggleUserToAdd = (userId: number) => {
        setSelectedUsersToAdd((prev) =>
            prev.includes(userId)
                ? prev.filter((id) => id !== userId)
                : [...prev, userId]
        );
    };

    const toggleUserToRemove = (userId: number) => {
        setSelectedUsersToRemove((prev) =>
            prev.includes(userId)
                ? prev.filter((id) => id !== userId)
                : [...prev, userId]
        );
    };

    const grantPermission = async (codename: string) => {
        try {
            await addPermissionsMutation.mutateAsync([codename]);
            toast.success("Permission granted");
        } catch (err) {
            toast.error("Failed to grant permission");
        }
    };

    const revokePermission = async (codename: string) => {
        try {
            const newPerms = groupPermissions
                .map((p) => p.codename)
                .filter((c) => c !== codename);
            await setPermissionsMutation.mutateAsync(newPerms);
            toast.success("Permission revoked");
        } catch (err) {
            toast.error("Failed to revoke permission");
        }
    };

    return (
        <div className="container mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                    <Link to="/editor/groups" className="hover:text-foreground">
                        Groups
                    </Link>
                    <span>/</span>
                    <span>{group.name}</span>
                </div>

                <div className="flex items-start justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <Users className="h-8 w-8 text-muted-foreground" />
                            <h1 className="text-2xl font-bold">{group.name}</h1>
                            {!group.is_custom && group.preset_key && (
                                <Badge variant="outline">{group.preset_key}</Badge>
                            )}
                        </div>
                        {group.description && (
                            <p className="text-muted-foreground">{group.description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant="outline">{group.member_count} members</Badge>
                        <Badge variant="secondary">
                            {group.permission_count} permissions
                        </Badge>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="users" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="users" className="gap-2">
                        <Users className="h-4 w-4" />
                        Members
                    </TabsTrigger>
                    <TabsTrigger value="permissions" className="gap-2">
                        <Shield className="h-4 w-4" />
                        Permissions
                    </TabsTrigger>
                </TabsList>

                {/* Users Tab */}
                <TabsContent value="users">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>Group Members</CardTitle>
                                    <CardDescription>
                                        Users assigned to the {group.name} group
                                    </CardDescription>
                                </div>
                                <div className="flex gap-2">
                                    {selectedUsersToRemove.length > 0 && (
                                        <Button
                                            variant="destructive"
                                            size="sm"
                                            onClick={handleRemoveUsers}
                                            disabled={removeMemberMutation.isPending}
                                        >
                                            {removeMemberMutation.isPending ? (
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            ) : (
                                                <UserMinus className="h-4 w-4 mr-2" />
                                            )}
                                            Remove ({selectedUsersToRemove.length})
                                        </Button>
                                    )}
                                    <Dialog open={showAddUsersDialog} onOpenChange={setShowAddUsersDialog}>
                                        <DialogTrigger asChild>
                                            <Button size="sm">
                                                <UserPlus className="h-4 w-4 mr-2" />
                                                Add Members
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent className="max-w-2xl">
                                            <DialogHeader>
                                                <DialogTitle>Add Members to {group.name}</DialogTitle>
                                                <DialogDescription>
                                                    Select users to add to this group
                                                </DialogDescription>
                                            </DialogHeader>
                                            <div className="space-y-4">
                                                <div className="relative">
                                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                                    <Input
                                                        placeholder="Search users..."
                                                        value={userSearchQuery}
                                                        onChange={(e) => setUserSearchQuery(e.target.value)}
                                                        className="pl-9"
                                                    />
                                                </div>
                                                <div className="max-h-[300px] overflow-y-auto border rounded-md">
                                                    <Table>
                                                        <TableHeader>
                                                            <TableRow>
                                                                <TableHead className="w-12"></TableHead>
                                                                <TableHead>User</TableHead>
                                                                <TableHead>Email</TableHead>
                                                            </TableRow>
                                                        </TableHeader>
                                                        <TableBody>
                                                            {filteredUsersToAdd.length === 0 ? (
                                                                <TableRow>
                                                                    <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                                                                        No users available to add
                                                                    </TableCell>
                                                                </TableRow>
                                                            ) : (
                                                                filteredUsersToAdd.map((user) => (
                                                                    <TableRow key={user.id}>
                                                                        <TableCell>
                                                                            <Checkbox
                                                                                checked={selectedUsersToAdd.includes(user.id)}
                                                                                onCheckedChange={() => toggleUserToAdd(user.id)}
                                                                            />
                                                                        </TableCell>
                                                                        <TableCell>
                                                                            {user.first_name} {user.last_name}
                                                                            {!user.first_name && !user.last_name && user.username}
                                                                        </TableCell>
                                                                        <TableCell>{user.email}</TableCell>
                                                                    </TableRow>
                                                                ))
                                                            )}
                                                        </TableBody>
                                                    </Table>
                                                </div>
                                            </div>
                                            <DialogFooter>
                                                <Button variant="outline" onClick={() => setShowAddUsersDialog(false)}>
                                                    Cancel
                                                </Button>
                                                <Button
                                                    onClick={handleAddUsers}
                                                    disabled={selectedUsersToAdd.length === 0 || addMemberMutation.isPending}
                                                >
                                                    {addMemberMutation.isPending && (
                                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                    )}
                                                    Add {selectedUsersToAdd.length} Member(s)
                                                </Button>
                                            </DialogFooter>
                                        </DialogContent>
                                    </Dialog>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-12"></TableHead>
                                        <TableHead>User</TableHead>
                                        <TableHead>Email</TableHead>
                                        <TableHead>Added</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {membersLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className="text-center py-8">
                                                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                                            </TableCell>
                                        </TableRow>
                                    ) : groupMembers.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                                                No members in this group
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        groupMembers.map((member) => (
                                            <TableRow key={member.id}>
                                                <TableCell>
                                                    <Checkbox
                                                        checked={selectedUsersToRemove.includes(member.user)}
                                                        onCheckedChange={() => toggleUserToRemove(member.user)}
                                                    />
                                                </TableCell>
                                                <TableCell>{member.user_name}</TableCell>
                                                <TableCell>{member.user_email}</TableCell>
                                                <TableCell className="text-muted-foreground text-sm">
                                                    {new Date(member.granted_at).toLocaleDateString()}
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Permissions Tab */}
                <TabsContent value="permissions">
                    <Card>
                        <CardHeader>
                            <div>
                                <CardTitle>Group Permissions</CardTitle>
                                <CardDescription>
                                    Click a permission to grant or revoke it
                                </CardDescription>
                            </div>
                            <div className="flex gap-2 mt-4">
                                <div className="relative flex-1">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        placeholder="Search permissions..."
                                        value={permissionSearchQuery}
                                        onChange={(e) => setPermissionSearchQuery(e.target.value)}
                                        className="pl-9"
                                    />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 gap-4">
                                {/* Granted Permissions */}
                                <div className="border rounded-lg">
                                    <div className="bg-green-500/10 border-b px-4 py-2 flex items-center gap-2">
                                        <ShieldPlus className="h-4 w-4 text-green-600" />
                                        <span className="font-medium text-green-700 dark:text-green-400">
                                            Granted ({filteredGrantedPermissions.length})
                                        </span>
                                    </div>
                                    <div className="max-h-[400px] overflow-y-auto">
                                        {filteredGrantedPermissions.length === 0 ? (
                                            <p className="text-muted-foreground text-center py-8 text-sm">
                                                No permissions granted
                                            </p>
                                        ) : (
                                            <div className="divide-y">
                                                {filteredGrantedPermissions.map((perm) => (
                                                    <button
                                                        key={perm.codename}
                                                        onClick={() => revokePermission(perm.codename)}
                                                        disabled={setPermissionsMutation.isPending}
                                                        className="w-full text-left px-4 py-2 hover:bg-red-500/10 transition-colors disabled:opacity-50 group"
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <div className="text-sm font-medium">{perm.name}</div>
                                                                <div className="text-xs text-muted-foreground">
                                                                    <code>{perm.codename}</code>
                                                                    {perm.content_type && (
                                                                        <>
                                                                            <span className="mx-1">·</span>
                                                                            {perm.content_type}
                                                                        </>
                                                                    )}
                                                                </div>
                                                            </div>
                                                            <ShieldMinus className="h-4 w-4 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                        </div>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Available Permissions */}
                                <div className="border rounded-lg">
                                    <div className="bg-muted/50 border-b px-4 py-2 flex items-center gap-2">
                                        <ShieldMinus className="h-4 w-4 text-muted-foreground" />
                                        <span className="font-medium text-muted-foreground">
                                            Available ({filteredAvailablePermissions.length})
                                        </span>
                                    </div>
                                    <div className="max-h-[400px] overflow-y-auto">
                                        {filteredAvailablePermissions.length === 0 ? (
                                            <p className="text-muted-foreground text-center py-8 text-sm">
                                                No available permissions
                                            </p>
                                        ) : (
                                            <div className="divide-y">
                                                {filteredAvailablePermissions.map((perm) => (
                                                    <button
                                                        key={perm.codename}
                                                        onClick={() => grantPermission(perm.codename)}
                                                        disabled={addPermissionsMutation.isPending}
                                                        className="w-full text-left px-4 py-2 hover:bg-green-500/10 transition-colors disabled:opacity-50 group"
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <div className="text-sm font-medium">{perm.name}</div>
                                                                <div className="text-xs text-muted-foreground">
                                                                    <code>{perm.codename}</code>
                                                                    {perm.content_type && (
                                                                        <>
                                                                            <span className="mx-1">·</span>
                                                                            {perm.content_type}
                                                                        </>
                                                                    )}
                                                                </div>
                                                            </div>
                                                            <ShieldPlus className="h-4 w-4 text-green-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                        </div>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
