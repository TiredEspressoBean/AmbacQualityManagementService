/**
 * Pick a location — a record, so the value is its id. Options show the full path
 * (Main Stores / Rack 3 / Bin B) and search matches the code too. Anyone who can
 * receive or move stock can add one from here ("Add location “Rack 9”"); it's created
 * at the top level, and a lead can file it under its parent later on Locations.
 */
import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { Combobox, type ComboboxProps } from "@/components/ui/combobox";
import { api } from "@/lib/api/generated";
import { locationSummaryOptions } from "@/hooks/useLocations";
import { usePermissionSet } from "@/hooks/useMyPermissions";

const errorOf = (err: unknown, fallback: string) => {
    const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
    const first = data && Object.values(data)[0];
    return (Array.isArray(first) ? String(first[0]) : typeof first === "string" ? first : null) ?? fallback;
};

type Props = Omit<ComboboxProps, "options" | "allowCreate" | "value" | "onChange" | "action"> & {
    /** The location's id. */
    value: string | null | undefined;
    onChange: (id: string | null) => void;
    /** Offer only held-only locations (or leave them out). Default: everything active. */
    heldOnly?: boolean;
};

export const LocationCombobox = React.forwardRef<HTMLButtonElement, Props>(function LocationCombobox(
    { value, onChange, heldOnly, placeholder = "Choose a location", ...props }, ref,
) {
    const qc = useQueryClient();
    const { has } = usePermissionSet();
    const { data, isLoading } = useQuery(locationSummaryOptions());
    const options = React.useMemo(() => (data ?? [])
        .filter((l) => (l.is_active || l.id === value) && (heldOnly === undefined || l.held_only === heldOnly))
        .map((l) => ({
            value: l.id,
            label: l.path,
            keywords: [l.name, l.code].filter(Boolean),
            description: [l.code, l.held_only ? "Held stock only" : "", l.receiving_dock ? "Receiving dock" : ""]
                .filter(Boolean).join(" · ") || undefined,
        })), [data, value, heldOnly]);
    const create = useMutation({
        mutationFn: (name: string) => api.api_StorageLocations_create({ name }),
        onSuccess: (loc) => {
            void qc.invalidateQueries({ queryKey: ["locations"] });
            onChange(loc.id);
            toast.success(`Added ${loc.name}.`);
        },
        onError: (e) => toast.error(errorOf(e, "Could not add the location")),
    });
    return (
        <Combobox
            ref={ref}
            value={value || null}
            onChange={onChange}
            options={options}
            loading={isLoading || create.isPending}
            clearLabel="No location"
            placeholder={placeholder}
            searchPlaceholder="Search locations…"
            emptyText="No location by that name."
            action={has("add_storagelocation") ? {
                label: (q) => q.trim() ? `Add location “${q.trim()}”` : "Add a location (type its name)",
                onSelect: (q) => { if (q.trim()) create.mutate(q.trim()); },
                icon: <Plus className="mr-2 h-4 w-4" />,
            } : undefined}
            {...props}
        />
    );
});
