import { useState } from "react";
import { Check, ChevronsUpDown, Plus, User as UserIcon, Users as UsersIcon, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";

/**
 * Unified "Required Approvers" widget for the approval-template editor.
 *
 * Visual model: one ordered list of requirement rows. Each row is
 * either a specific person (👤) or a role group (👥). Storage model:
 * two flat M2M fields on the template — `default_approvers` (User IDs)
 * and `default_groups` (TenantGroup IDs). The widget projects both
 * arrays as a single list and splits them back on every onChange.
 *
 * Per-group thresholds aren't supported in v1 because the model has
 * only a single global `default_threshold` field. When the flow type
 * is THRESHOLD, that one threshold applies to the combined approver
 * pool. If a tenant later needs "2 of QA + 1 of PM" semantics, that's
 * a follow-up adding a `GroupApproverRequirement` through-table.
 *
 * Visual order is presentational only — no row index is persisted, so
 * reload returns rows in the order users + groups happen to come back
 * from the API.
 */
export type ApproverRequirementsValue = {
    approvers: number[];
    groups: string[];
};

type Props = {
    value: ApproverRequirementsValue;
    onChange: (next: ApproverRequirementsValue) => void;
    disabled?: boolean;
};

export function RequiredApproversField({ value, onChange, disabled }: Props) {
    const [userOpen, setUserOpen] = useState(false);
    const [groupOpen, setGroupOpen] = useState(false);

    const { data: usersResp } = useRetrieveUsers();
    const { data: groupsResp } = useTenantGroups();
    const users = (usersResp?.results ?? []) as Array<{
        id: number;
        full_name?: string | null;
        username?: string | null;
        email?: string | null;
    }>;
    const groups = (groupsResp?.results ?? []) as Array<{
        id: string;
        name: string;
        user_count?: number;
    }>;

    const userById = new Map(users.map((u) => [u.id, u]));
    const groupById = new Map(groups.map((g) => [g.id, g]));

    const selectedUsers = value.approvers
        .map((id) => userById.get(id))
        .filter((u): u is NonNullable<typeof u> => !!u);
    const selectedGroups = value.groups
        .map((id) => groupById.get(id))
        .filter((g): g is NonNullable<typeof g> => !!g);

    const toggleUser = (id: number) => {
        if (value.approvers.includes(id)) {
            onChange({ ...value, approvers: value.approvers.filter((x) => x !== id) });
        } else {
            onChange({ ...value, approvers: [...value.approvers, id] });
        }
    };
    const toggleGroup = (id: string) => {
        if (value.groups.includes(id)) {
            onChange({ ...value, groups: value.groups.filter((x) => x !== id) });
        } else {
            onChange({ ...value, groups: [...value.groups, id] });
        }
    };
    const removeUser = (id: number) =>
        onChange({ ...value, approvers: value.approvers.filter((x) => x !== id) });
    const removeGroup = (id: string) =>
        onChange({ ...value, groups: value.groups.filter((x) => x !== id) });

    const isEmpty = selectedUsers.length === 0 && selectedGroups.length === 0;

    return (
        <div className="space-y-3">
            <div
                className={cn(
                    "rounded-md border p-3 space-y-2",
                    isEmpty && "border-dashed",
                )}
            >
                {isEmpty && (
                    <p className="text-sm text-muted-foreground italic">
                        No approvers configured. Add specific people, role groups,
                        or both — both can coexist.
                    </p>
                )}

                {selectedUsers.map((u) => (
                    <Row
                        key={`user-${u.id}`}
                        icon={<UserIcon className="h-4 w-4 text-primary" />}
                        kindBadge="Person"
                        label={u.full_name || u.username || u.email || `User #${u.id}`}
                        onRemove={() => removeUser(u.id)}
                        disabled={disabled}
                    />
                ))}

                {selectedGroups.map((g) => (
                    <Row
                        key={`group-${g.id}`}
                        icon={<UsersIcon className="h-4 w-4 text-amber-600" />}
                        kindBadge="Role"
                        label={g.name}
                        sublabel={
                            typeof g.user_count === "number"
                                ? `${g.user_count} member${g.user_count === 1 ? "" : "s"} eligible`
                                : undefined
                        }
                        onRemove={() => removeGroup(g.id)}
                        disabled={disabled}
                    />
                ))}
            </div>

            <div className="flex gap-2">
                <Popover open={userOpen} onOpenChange={setUserOpen}>
                    <PopoverTrigger asChild>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={disabled}
                            className="flex-1"
                        >
                            <Plus className="h-4 w-4 mr-1" />
                            <UserIcon className="h-3.5 w-3.5 mr-1" />
                            Add Person
                            <ChevronsUpDown className="h-3.5 w-3.5 ml-auto opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 p-0" align="start">
                        <Command>
                            <CommandInput placeholder="Search users…" />
                            <CommandList>
                                <CommandEmpty>No users found.</CommandEmpty>
                                <CommandGroup>
                                    {users.map((u) => {
                                        const selected = value.approvers.includes(u.id);
                                        const display = u.full_name || u.username || u.email || `User #${u.id}`;
                                        return (
                                            <CommandItem
                                                key={u.id}
                                                value={display}
                                                onSelect={() => toggleUser(u.id)}
                                            >
                                                <Check
                                                    className={cn(
                                                        "h-4 w-4 mr-2",
                                                        selected ? "opacity-100" : "opacity-0",
                                                    )}
                                                />
                                                {display}
                                            </CommandItem>
                                        );
                                    })}
                                </CommandGroup>
                            </CommandList>
                        </Command>
                    </PopoverContent>
                </Popover>

                <Popover open={groupOpen} onOpenChange={setGroupOpen}>
                    <PopoverTrigger asChild>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={disabled}
                            className="flex-1"
                        >
                            <Plus className="h-4 w-4 mr-1" />
                            <UsersIcon className="h-3.5 w-3.5 mr-1" />
                            Add Role
                            <ChevronsUpDown className="h-3.5 w-3.5 ml-auto opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 p-0" align="start">
                        <Command>
                            <CommandInput placeholder="Search role groups…" />
                            <CommandList>
                                <CommandEmpty>No groups found.</CommandEmpty>
                                <CommandGroup>
                                    {groups.map((g) => {
                                        const selected = value.groups.includes(g.id);
                                        return (
                                            <CommandItem
                                                key={g.id}
                                                value={g.name}
                                                onSelect={() => toggleGroup(g.id)}
                                            >
                                                <Check
                                                    className={cn(
                                                        "h-4 w-4 mr-2",
                                                        selected ? "opacity-100" : "opacity-0",
                                                    )}
                                                />
                                                <span>{g.name}</span>
                                                {typeof g.user_count === "number" && (
                                                    <span className="ml-auto text-xs text-muted-foreground">
                                                        {g.user_count}
                                                    </span>
                                                )}
                                            </CommandItem>
                                        );
                                    })}
                                </CommandGroup>
                            </CommandList>
                        </Command>
                    </PopoverContent>
                </Popover>
            </div>

            <p className="text-xs text-muted-foreground">
                Specific people and role groups can both be configured at once.
                Order shown is presentational; sequential signature collection
                follows responder order, not list order.
            </p>
        </div>
    );
}

function Row({
    icon,
    kindBadge,
    label,
    sublabel,
    onRemove,
    disabled,
}: {
    icon: React.ReactNode;
    kindBadge: string;
    label: string;
    sublabel?: string;
    onRemove: () => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex items-center gap-2 rounded-md border bg-background p-2">
            <span className="shrink-0">{icon}</span>
            <Badge variant="outline" className="text-[10px]">{kindBadge}</Badge>
            <div className="flex-1 min-w-0">
                <div className="text-sm truncate">{label}</div>
                {sublabel && (
                    <div className="text-xs text-muted-foreground truncate">{sublabel}</div>
                )}
            </div>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onRemove}
                disabled={disabled}
                aria-label={`Remove ${label}`}
                className="h-6 w-6 p-0"
            >
                <X className="h-4 w-4" />
            </Button>
        </div>
    );
}
