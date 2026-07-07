/**
 * User Management — dedicated admin surface for managing tenant users.
 *
 * Replaces the generic ModelEditorPage UX at `/editor/users` with a purpose-
 * built admin tool: status pills, group chips, per-row actions, filter chips,
 * selection + bulk action bar, and a link out to the full-page workbook
 * (`/admin/users/bulk-invite`).
 *
 * UI mock for now — bulk actions emit toasts. The page wires up the read
 * path (real users list, real groups) so the layout is correct against real
 * data; the *write* actions await backend.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
    Search,
    UserPlus,
    MoreHorizontal,
    Mail,
    UserX,
    UserCheck,
    Users as UsersIcon,
    X,
    Edit,
    Link as LinkIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { useQueryClient } from "@tanstack/react-query";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { useSetUsersTenantActive } from "@/hooks/useSetUsersTenantActive";
import { useSendUserInvitation } from "@/hooks/useSendUserInvitation";
import { useAddUserToTenantGroup } from "@/hooks/useAddUserToTenantGroup";
import { InviteLinkDialog } from "@/components/users/InviteLinkDialog";
import { format, formatDistanceToNow } from "date-fns";

// ---------------------------------------------------------------------------
// Status derivation
// ---------------------------------------------------------------------------

type UserStatus = "active" | "inactive" | "pending_invite" | "expired_invite";

const STATUS_LABEL: Record<UserStatus, string> = {
    active: "Active",
    inactive: "Inactive",
    pending_invite: "Pending invite",
    expired_invite: "Expired invite",
};

const STATUS_VARIANT: Record<UserStatus, "default" | "secondary" | "destructive" | "outline"> = {
    active: "default",
    inactive: "secondary",
    pending_invite: "outline",
    expired_invite: "destructive",
};

/** Derive a status from User fields. "inactive" reflects the per-tenant
 *  membership being SUSPENDED (the tenant-scoped deactivation) OR the global
 *  account being disabled; pending/active otherwise. */
function deriveStatus(user: {
    is_active?: boolean | null;
    last_login?: string | null;
    tenant_membership_status?: string | null;
}): UserStatus {
    if (user.tenant_membership_status === "SUSPENDED") return "inactive";
    if (user.is_active === false) return "inactive";
    if (!user.last_login) return "pending_invite";
    return "active";
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const STATUS_FILTERS: { key: UserStatus | "all"; label: string }[] = [
    { key: "all", label: "All" },
    { key: "active", label: "Active" },
    { key: "pending_invite", label: "Pending invite" },
    { key: "expired_invite", label: "Expired invite" },
    { key: "inactive", label: "Inactive" },
];

export function UserManagementPage() {
    const navigate = useNavigate();
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState<UserStatus | "all">("all");
    const [groupFilter, setGroupFilter] = useState<string>("all");
    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [addToGroupOpen, setAddToGroupOpen] = useState(false);
    const [addToGroupId, setAddToGroupId] = useState<string>("");
    const [addToGroupSubmitting, setAddToGroupSubmitting] = useState(false);
    const [inviteLinkUrl, setInviteLinkUrl] = useState<string | null>(null);
    const [inviteLinkEmail, setInviteLinkEmail] = useState<string | undefined>(undefined);
    const [inviteLinkOpen, setInviteLinkOpen] = useState(false);

    const queryClient = useQueryClient();
    const { data: usersData, isLoading } = useRetrieveUsers({
        limit: 200,
        search: search || undefined,
    });
    const { data: groupsData } = useTenantGroups({ limit: 200 });
    const setTenantActive = useSetUsersTenantActive();
    const sendInvite = useSendUserInvitation();
    const addToGroup = useAddUserToTenantGroup();

    /** Invalidate the User list query — useUpdateUser's onSuccess only
     *  invalidates `["User"]` (capital), but the list hook uses `["user"]`
     *  (lowercase). Broad predicate covers both. */
    const invalidateUsers = () => {
        queryClient.invalidateQueries({
            predicate: (q) => {
                const k = q.queryKey?.[0];
                return k === "user" || k === "User";
            },
        });
    };

    const users = useMemo(() => usersData?.results ?? [], [usersData]);
    const groupNames = useMemo(
        () => (groupsData?.results ?? []).map((g) => g.name).sort(),
        [groupsData],
    );

    // Filtered + status-derived rows
    const rows = useMemo(() => {
        return users
            .map((u) => ({
                ...u,
                _status: deriveStatus({
                    is_active: u.is_active,
                    last_login: u.last_login ?? null,
                }),
                _groupNames: ((u as { groups?: { name?: string }[] }).groups ?? [])
                    .map((g) => g?.name)
                    .filter((n): n is string => Boolean(n)),
            }))
            .filter((u) => statusFilter === "all" || u._status === statusFilter)
            .filter((u) => groupFilter === "all" || u._groupNames.includes(groupFilter));
    }, [users, statusFilter, groupFilter]);

    const allOnPageSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));
    const someSelected = selected.size > 0;

    const toggleSelectAll = () => {
        if (allOnPageSelected) setSelected(new Set());
        else setSelected(new Set(rows.map((r) => r.id)));
    };
    const toggleOne = (id: number) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };
    const clearSelection = () => setSelected(new Set());

    // ---- Action handlers --------------------------------------------------

    /** Create (or surface an existing) invitation and show its copyable link.
     *  Doubles as email-free access recovery: accepting a fresh invite re-sets
     *  the user's password. Works for any user — active users get a new invite,
     *  users with a live pending invite get that invite's link back (400). */
    const handleInviteLink = async (userId: number, email: string) => {
        try {
            const data = await sendInvite.mutateAsync(userId);
            if (data?.invitation_url) {
                setInviteLinkUrl(data.invitation_url);
                setInviteLinkEmail(email);
                setInviteLinkOpen(true);
            }
            toast.success(`Invitation link ready for ${email}`);
        } catch (err) {
            // eslint-disable-next-line local/no-as-any -- axios error body needs verbose narrowing
            const apiError = (err as any)?.response?.data;
            if (apiError?.invitation_url) {
                setInviteLinkUrl(apiError.invitation_url);
                setInviteLinkEmail(email);
                setInviteLinkOpen(true);
                toast.info(`${email} already has a pending invitation — here's the link.`);
                return;
            }
            toast.error(`Failed to create invitation link for ${email}`, {
                description: err instanceof Error ? err.message : undefined,
            });
        }
    };

    const handleSetActive = async (userId: number, email: string, active: boolean) => {
        try {
            await setTenantActive.mutateAsync({ userIds: [userId], isActive: active });
            toast.success(`${active ? "Activated" : "Deactivated"} ${email}`);
            invalidateUsers();
        } catch (err) {
            toast.error(
                `Failed to ${active ? "activate" : "deactivate"} ${email}`,
                { description: err instanceof Error ? err.message : undefined },
            );
        }
    };

    /** Fan out a single-user mutation across the current selection.
     *  Reports successes / failures as one summary toast. Used for the
     *  bulk-bar Resend / Activate / Deactivate actions. */
    const handleBulkFanout = async (
        label: string,
        per: (userId: number, email: string) => Promise<unknown>,
    ) => {
        if (selected.size === 0) return;
        const targets = rows.filter((r) => selected.has(r.id));
        const results = await Promise.allSettled(
            targets.map((r) => per(r.id, r.email ?? "")),
        );
        const ok = results.filter((r) => r.status === "fulfilled").length;
        const fail = results.length - ok;
        if (fail === 0) {
            toast.success(`${label}: ${ok} user${ok === 1 ? "" : "s"}`);
        } else if (ok === 0) {
            toast.error(`${label} failed for all ${fail} user${fail === 1 ? "" : "s"}`);
        } else {
            toast.warning(`${label}: ${ok} succeeded, ${fail} failed`);
        }
        invalidateUsers();
        clearSelection();
    };

    const handleBulkResend = () =>
        handleBulkFanout("Resent invitations", (id) => sendInvite.mutateAsync(id));

    /** Activate/deactivate the current selection in ONE tenant-scoped call.
     *  The backend skips the requesting user, so updated_count may be < the
     *  number selected — report the server's count. */
    const handleBulkSetActive = async (active: boolean) => {
        if (selected.size === 0) return;
        const userIds = [...selected];
        const label = active ? "Activated" : "Deactivated";
        try {
            const res = await setTenantActive.mutateAsync({ userIds, isActive: active });
            const n = res?.updated_count ?? userIds.length;
            toast.success(`${label}: ${n} user${n === 1 ? "" : "s"}`);
        } catch (err) {
            toast.error(
                `${active ? "Activate" : "Deactivate"} failed`,
                { description: err instanceof Error ? err.message : undefined },
            );
        }
        invalidateUsers();
        clearSelection();
    };
    const handleBulkActivate = () => handleBulkSetActive(true);
    const handleBulkDeactivate = () => handleBulkSetActive(false);
    const handleBulkAddToGroup = () => {
        if (selected.size === 0) return;
        setAddToGroupId(""); // reset previous pick
        setAddToGroupOpen(true);
    };

    const handleConfirmAddToGroup = async () => {
        if (!addToGroupId || selected.size === 0) return;
        const group = (groupsData?.results ?? []).find((g) => g.id === addToGroupId);
        const groupLabel = group?.name ?? "group";
        const targets = rows.filter((r) => selected.has(r.id));

        setAddToGroupSubmitting(true);
        try {
            const results = await Promise.allSettled(
                targets.map((r) =>
                    addToGroup.mutateAsync({ groupId: addToGroupId, userId: r.id }),
                ),
            );
            // Buckets: added cleanly | already a member (skipped) | failed
            let added = 0;
            let alreadyMember = 0;
            let failed = 0;
            for (const res of results) {
                if (res.status === "fulfilled") {
                    if ((res.value as { alreadyMember?: boolean })?.alreadyMember) {
                        alreadyMember++;
                    } else {
                        added++;
                    }
                } else {
                    failed++;
                }
            }
            if (failed === 0 && alreadyMember === 0) {
                toast.success(`Added ${added} user${added === 1 ? "" : "s"} to ${groupLabel}`);
            } else if (failed === 0) {
                toast.success(`${groupLabel}: ${added} added, ${alreadyMember} already a member`);
            } else if (added === 0 && alreadyMember === 0) {
                toast.error(`Failed to add any user to ${groupLabel}`);
            } else {
                toast.warning(
                    `${groupLabel}: ${added} added, ${alreadyMember} already a member, ${failed} failed`,
                );
            }
            invalidateUsers();
            clearSelection();
            setAddToGroupOpen(false);
        } finally {
            setAddToGroupSubmitting(false);
        }
    };

    // ---- Counts for chip badges -------------------------------------------

    const counts = useMemo(() => {
        const c: Record<UserStatus | "all", number> = {
            all: users.length,
            active: 0,
            inactive: 0,
            pending_invite: 0,
            expired_invite: 0,
        };
        for (const u of users) {
            const s = deriveStatus({
                is_active: u.is_active,
                last_login: u.last_login ?? null,
            });
            c[s]++;
        }
        return c;
    }, [users]);

    return (
        <TooltipProvider>
            <div className="container mx-auto p-6 max-w-7xl space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <UsersIcon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">User Management</h1>
                            <p className="text-sm text-muted-foreground">
                                {users.length} user{users.length === 1 ? "" : "s"} in this organization
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            onClick={() => navigate({ to: "/UserForm/create" })}
                        >
                            <UserPlus className="h-4 w-4 mr-1.5" />
                            Add user
                        </Button>
                        <Button onClick={() => navigate({ to: "/admin/users/bulk-invite" })}>
                            <UserPlus className="h-4 w-4 mr-1.5" />
                            Bulk Actions
                        </Button>
                    </div>
                </div>

                {/* Filter chips + search */}
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex flex-wrap gap-1.5">
                        {STATUS_FILTERS.map((f) => (
                            <button
                                key={f.key}
                                type="button"
                                onClick={() => setStatusFilter(f.key)}
                                className={
                                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition " +
                                    (statusFilter === f.key
                                        ? "bg-primary text-primary-foreground border-primary"
                                        : "bg-background hover:bg-muted")
                                }
                            >
                                {f.label}
                                <span className="text-[10px] opacity-70">
                                    {counts[f.key as keyof typeof counts] ?? 0}
                                </span>
                            </button>
                        ))}
                    </div>
                    <div className="h-6 w-px bg-border" />
                    <Select value={groupFilter} onValueChange={setGroupFilter}>
                        <SelectTrigger className="h-8 w-[180px] text-xs">
                            <SelectValue placeholder="All groups" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All groups</SelectItem>
                            {groupNames.map((g) => (
                                <SelectItem key={g} value={g}>
                                    {g}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="relative ml-auto">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search by name or email…"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="h-8 w-[280px] pl-8 text-sm"
                        />
                    </div>
                </div>

                {/* Bulk action bar */}
                {someSelected && (
                    <div className="flex items-center gap-3 rounded-md border bg-primary/5 px-4 py-2 text-sm">
                        <span className="font-medium">
                            {selected.size} selected
                        </span>
                        <div className="h-4 w-px bg-border" />
                        <Button size="sm" variant="ghost" onClick={handleBulkResend}>
                            <Mail className="h-4 w-4 mr-1.5" />
                            Resend invite
                        </Button>
                        <Button size="sm" variant="ghost" onClick={handleBulkAddToGroup}>
                            Add to group
                        </Button>
                        <Button size="sm" variant="ghost" onClick={handleBulkActivate}>
                            <UserCheck className="h-4 w-4 mr-1.5" />
                            Activate
                        </Button>
                        <Button size="sm" variant="ghost" onClick={handleBulkDeactivate}>
                            <UserX className="h-4 w-4 mr-1.5" />
                            Deactivate
                        </Button>
                        <Button size="sm" variant="ghost" className="ml-auto" onClick={clearSelection}>
                            <X className="h-4 w-4 mr-1.5" />
                            Clear
                        </Button>
                    </div>
                )}

                {/* Table */}
                <div className="rounded-md border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/50 text-left">
                            <tr>
                                <th className="px-3 py-2 w-10">
                                    <Checkbox
                                        checked={allOnPageSelected}
                                        onCheckedChange={toggleSelectAll}
                                        aria-label="Select all"
                                    />
                                </th>
                                <th className="px-3 py-2 font-medium">Name / Email</th>
                                <th className="px-3 py-2 font-medium">Status</th>
                                <th className="px-3 py-2 font-medium">Groups</th>
                                <th className="px-3 py-2 font-medium">Last login</th>
                                <th className="px-3 py-2 font-medium">Joined</th>
                                <th className="px-3 py-2 w-12"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading && (
                                <tr>
                                    <td colSpan={7} className="px-3 py-8 text-center text-sm text-muted-foreground">
                                        Loading users…
                                    </td>
                                </tr>
                            )}
                            {!isLoading && rows.length === 0 && (
                                <tr>
                                    <td colSpan={7} className="px-3 py-8 text-center text-sm text-muted-foreground">
                                        No users match the current filters.
                                    </td>
                                </tr>
                            )}
                            {rows.map((u) => {
                                const fullName = `${u.first_name || ""} ${u.last_name || ""}`.trim();
                                const lastLogin = u.last_login;
                                return (
                                    <tr
                                        key={u.id}
                                        className={
                                            "border-t hover:bg-muted/30 " +
                                            (selected.has(u.id) ? "bg-primary/5" : "")
                                        }
                                    >
                                        <td className="px-3 py-2">
                                            <Checkbox
                                                checked={selected.has(u.id)}
                                                onCheckedChange={() => toggleOne(u.id)}
                                                aria-label={`Select ${u.email}`}
                                            />
                                        </td>
                                        <td className="px-3 py-2">
                                            <div className="flex flex-col">
                                                <span className="font-medium">
                                                    {fullName || u.username || u.email}
                                                </span>
                                                {fullName && (
                                                    <span className="text-xs text-muted-foreground">{u.email}</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-3 py-2">
                                            <Badge variant={STATUS_VARIANT[u._status]} className="text-[10px]">
                                                {STATUS_LABEL[u._status]}
                                            </Badge>
                                        </td>
                                        <td className="px-3 py-2">
                                            <div className="flex flex-wrap gap-1">
                                                {u._groupNames.length === 0 ? (
                                                    <span className="text-xs text-muted-foreground">—</span>
                                                ) : (
                                                    u._groupNames.slice(0, 3).map((g) => (
                                                        <Badge key={g} variant="secondary" className="text-[10px]">
                                                            {g}
                                                        </Badge>
                                                    ))
                                                )}
                                                {u._groupNames.length > 3 && (
                                                    <Badge variant="outline" className="text-[10px]">
                                                        +{u._groupNames.length - 3}
                                                    </Badge>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-3 py-2">
                                            {lastLogin ? (
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <span className="text-xs text-muted-foreground cursor-default">
                                                            {formatDistanceToNow(new Date(lastLogin), { addSuffix: true })}
                                                        </span>
                                                    </TooltipTrigger>
                                                    <TooltipContent>
                                                        {format(new Date(lastLogin), "PPpp")}
                                                    </TooltipContent>
                                                </Tooltip>
                                            ) : (
                                                <span className="text-xs text-muted-foreground italic">never</span>
                                            )}
                                        </td>
                                        <td className="px-3 py-2 text-xs text-muted-foreground">
                                            {u.date_joined
                                                ? format(new Date(u.date_joined), "MMM d, yyyy")
                                                : "—"}
                                        </td>
                                        <td className="px-3 py-2">
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-7 w-7">
                                                        <MoreHorizontal className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem
                                                        onClick={() => navigate({
                                                            to: "/UserForm/edit/$id",
                                                            params: { id: String(u.id) },
                                                        })}
                                                    >
                                                        <Edit className="h-4 w-4 mr-2" />
                                                        Edit profile
                                                    </DropdownMenuItem>
                                                    {u._status === "pending_invite" || u._status === "expired_invite" ? (
                                                        <DropdownMenuItem onClick={() => handleInviteLink(u.id, u.email ?? "")}>
                                                            <Mail className="h-4 w-4 mr-2" />
                                                            Resend invitation
                                                        </DropdownMenuItem>
                                                    ) : null}
                                                    <DropdownMenuItem onClick={() => handleInviteLink(u.id, u.email ?? "")}>
                                                        <LinkIcon className="h-4 w-4 mr-2" />
                                                        Copy access link
                                                    </DropdownMenuItem>
                                                    <DropdownMenuSeparator />
                                                    {u.is_active ? (
                                                        <DropdownMenuItem
                                                            onClick={() => handleSetActive(u.id, u.email ?? "", false)}
                                                            className="text-destructive focus:text-destructive"
                                                        >
                                                            <UserX className="h-4 w-4 mr-2" />
                                                            Deactivate
                                                        </DropdownMenuItem>
                                                    ) : (
                                                        <DropdownMenuItem onClick={() => handleSetActive(u.id, u.email ?? "", true)}>
                                                            <UserCheck className="h-4 w-4 mr-2" />
                                                            Activate
                                                        </DropdownMenuItem>
                                                    )}
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Bulk "Add to group" picker dialog */}
            <Dialog open={addToGroupOpen} onOpenChange={(o) => !addToGroupSubmitting && setAddToGroupOpen(o)}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Add to group</DialogTitle>
                        <DialogDescription>
                            Add {selected.size} selected user{selected.size === 1 ? "" : "s"} to a tenant group.
                            Users already in the group are skipped.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-2">
                        <Select value={addToGroupId} onValueChange={setAddToGroupId}>
                            <SelectTrigger>
                                <SelectValue placeholder="Pick a group…" />
                            </SelectTrigger>
                            <SelectContent>
                                {(groupsData?.results ?? []).length === 0 && (
                                    <SelectItem value="__empty__" disabled>
                                        No groups defined
                                    </SelectItem>
                                )}
                                {(groupsData?.results ?? []).map((g) => (
                                    <SelectItem key={g.id} value={g.id}>
                                        {g.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setAddToGroupOpen(false)}
                            disabled={addToGroupSubmitting}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleConfirmAddToGroup}
                            disabled={!addToGroupId || addToGroupSubmitting}
                        >
                            {addToGroupSubmitting
                                ? "Adding…"
                                : `Add ${selected.size} user${selected.size === 1 ? "" : "s"}`}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <InviteLinkDialog
                open={inviteLinkOpen}
                onOpenChange={setInviteLinkOpen}
                url={inviteLinkUrl}
                email={inviteLinkEmail}
            />
        </TooltipProvider>
    );
}