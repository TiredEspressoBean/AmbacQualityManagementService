/**
 * A storage location: free text, with the locations already in use (on material lots
 * and on equipment) offered as you type, so "Rack 4" isn't also "rack4" and "Rack 04".
 * Typing one that isn't listed uses it as is.
 */
import * as React from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { Combobox, type ComboboxProps } from "@/components/ui/combobox";
import { api } from "@/lib/api/generated";

export const locationsOptions = () =>
    queryOptions({
        queryKey: ["storage-locations"] as const,
        queryFn: () => api.api_MaterialLots_locations_retrieve() as Promise<string[]>,
        staleTime: 5 * 60_000,
    });

type Props = Omit<ComboboxProps, "options" | "allowCreate" | "value" | "onChange"> & {
    value: string | null | undefined;
    /** Blank clears it to "". */
    onChange: (value: string) => void;
};

export const LocationCombobox = React.forwardRef<HTMLButtonElement, Props>(function LocationCombobox(
    { value, onChange, placeholder = "Choose or type a location", ...props }, ref,
) {
    const { data, isLoading } = useQuery(locationsOptions());
    const options = React.useMemo(() => (data ?? []).map((l) => ({ value: l, label: l })), [data]);
    return (
        <Combobox
            ref={ref}
            allowCreate
            value={value || null}
            onChange={(v) => onChange(v ?? "")}
            options={options}
            loading={isLoading}
            clearLabel="No location"
            placeholder={placeholder}
            searchPlaceholder="Type a location…"
            emptyText="No locations yet — type one."
            {...props}
        />
    );
});
