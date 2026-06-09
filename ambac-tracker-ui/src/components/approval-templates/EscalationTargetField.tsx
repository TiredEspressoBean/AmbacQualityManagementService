import { useState } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    const [open, setOpen] = useState(false);
    const { data: usersResp } = useRetrieveUsers();
    const users = (usersResp?.results ?? []) as Array<{
        id: number;
        full_name?: string | null;
        username?: string | null;
        email?: string | null;
    }>;

    const selected = users.find((u) => u.id === value);
    const display = selected
        ? (selected.full_name || selected.username || selected.email || `User #${selected.id}`)
        : null;

    return (
        <div className="flex items-center gap-2">
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        type="button"
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        disabled={disabled}
                        className={cn(
                            "flex-1 justify-between font-normal",
                            !value && "text-muted-foreground",
                        )}
                    >
                        {display ?? "Pick a user (optional)"}
                        <ChevronsUpDown className="h-4 w-4 opacity-50" />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="start">
                    <Command>
                        <CommandInput placeholder="Search users…" />
                        <CommandList>
                            <CommandEmpty>No users found.</CommandEmpty>
                            <CommandGroup>
                                {users.map((u) => {
                                    const label = u.full_name || u.username || u.email || `User #${u.id}`;
                                    return (
                                        <CommandItem
                                            key={u.id}
                                            value={label}
                                            onSelect={() => {
                                                onChange(u.id);
                                                setOpen(false);
                                            }}
                                        >
                                            <Check
                                                className={cn(
                                                    "h-4 w-4 mr-2",
                                                    value === u.id ? "opacity-100" : "opacity-0",
                                                )}
                                            />
                                            {label}
                                        </CommandItem>
                                    );
                                })}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>
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
