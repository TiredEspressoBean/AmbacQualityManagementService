/**
 * What a lot is stock of: a raw material (`material`) or a bought part
 * (`material_type`, a PartType) — one or the other, never both, as the lot holds it.
 * Values are encoded `m:<id>` / `p:<id>` so one picker can offer both kinds.
 */
import * as React from "react";
import { useMemo } from "react";

import { Combobox, type ComboboxProps } from "@/components/ui/combobox";
import { useMaterialOptions } from "@/hooks/useMaterials";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";

export type StockItem = { kind: "material" | "part"; id: string; preferredSupplier?: string | null };

export const encodeStockItem = (kind: StockItem["kind"], id: string) => `${kind === "material" ? "m" : "p"}:${id}`;

export function decodeStockItem(value: string | null | undefined): Pick<StockItem, "kind" | "id"> | null {
    if (!value) return null;
    const [k, ...rest] = value.split(":");
    const id = rest.join(":");
    if (!id || (k !== "m" && k !== "p")) return null;
    return { kind: k === "m" ? "material" : "part", id };
}

/** The lot fields for a picked item: `{ material }` or `{ material_type }`. */
export function stockItemFields(value: string | null | undefined): { material?: string; material_type?: string } {
    const item = decodeStockItem(value);
    if (!item) return {};
    return item.kind === "material" ? { material: item.id } : { material_type: item.id };
}

/** Options and a name → value lookup, for pasting a spreadsheet of item names. */
export function useStockItems() {
    const materials = useMaterialOptions();
    const partTypes = useRetrievePartTypes({ limit: 500 });
    return useMemo(() => {
        const mats = materials.data?.results ?? [];
        const parts = partTypes.data?.results ?? [];
        const options = [
            ...mats.map((m) => ({
                value: encodeStockItem("material", String(m.id)), label: m.name, group: "Materials",
            })),
            ...parts.map((p) => ({
                value: encodeStockItem("part", String(p.id)), label: p.name, group: "Part types",
            })),
        ];
        const byName = new Map<string, string>();
        for (const o of options) if (!byName.has(o.label.toLowerCase())) byName.set(o.label.toLowerCase(), o.value);
        const supplierOf = new Map<string, string | null>([
            ...mats.map((m) => [encodeStockItem("material", String(m.id)), m.preferred_supplier ? String(m.preferred_supplier) : null] as [string, string | null]),
            ...parts.map((p) => [encodeStockItem("part", String(p.id)), p.preferred_supplier ? String(p.preferred_supplier) : null] as [string, string | null]),
        ]);
        return { options, byName, supplierOf, isLoading: materials.isLoading || partTypes.isLoading };
    }, [materials.data, materials.isLoading, partTypes.data, partTypes.isLoading]);
}

type Props = Omit<ComboboxProps, "options"> & { items?: ReturnType<typeof useStockItems> };

export const StockItemCombobox = React.forwardRef<HTMLButtonElement, Props>(function StockItemCombobox(
    { items, placeholder = "Select a material or part", ...props }, ref,
) {
    const own = useStockItems();
    const src = items ?? own;
    return (
        <Combobox
            ref={ref}
            options={src.options}
            loading={src.isLoading}
            placeholder={placeholder}
            searchPlaceholder="Search materials and parts…"
            emptyText="Nothing matches."
            {...props}
        />
    );
});
