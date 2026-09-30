import { Combobox } from "@/components/ui/combobox";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";

/**
 * Single-user picker for `ApprovalTemplate.escalate_to`.
 *
 * Model has `escalate_to` as a User FK (not a group), so this is a
 * single-select user picker with a clear button. Used inside the
 * approval-template editor next to the Escalation Days field.
 */
type Props = {
    value: number | null;
    onChange: (next: number | null) => void;
    disabled?: boolean;
};

export function EscalationTargetField({ value, onChange, disabled }: Props) {
    const { data: usersResp } = useRetrieveUsers();
    const users = (usersResp?.results ?? []) as Array<{
        id: number;
        full_name?: string | null;
        username?: string | null;
        email?: string | null;
    }>;


    return (
        <div className="flex items-center gap-2">
            <Combobox
                className="flex-1"
                contentClassName="w-80"
                value={value === null ? null : String(value)}
                onChange={(v) => onChange(v === null ? null : Number(v))}
                options={users.map((u) => ({
                    value: String(u.id),
                    label: u.full_name || u.username || u.email || `User #${u.id}`,
                    ...(u.email && u.full_name ? { description: u.email } : {}),
                }))}
                disabled={disabled}
                placeholder="Pick a user (optional)"
                searchPlaceholder="Search users…"
                emptyText="No users found."
            />
            {value !== null && (
                <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => onChange(null)}
                    disabled={disabled}
                    aria-label="Clear escalation target"
                    className="h-9 w-9 p-0"
                >
                    <X className="h-4 w-4" />
                </Button>
            )}
        </div>
    );
}
