import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export type PurchaseUnit = "STOCK" | "BOX" | "LB";

export type ReceivingControls = {
    purchase_unit: PurchaseUnit;
    units_per_purchase_unit: string | null;
    requires_coc: boolean;
    requires_heat_number: boolean;
};

export const DEFAULT_RECEIVING_CONTROLS: ReceivingControls = {
    purchase_unit: "STOCK",
    units_per_purchase_unit: null,
    requires_coc: false,
    requires_heat_number: false,
};

/** Read the four controls off a Material or PartTypes record. */
export function receivingControlsOf(r: Partial<ReceivingControls> | undefined | null): ReceivingControls {
    return {
        purchase_unit: (r?.purchase_unit as PurchaseUnit) ?? "STOCK",
        units_per_purchase_unit: r?.units_per_purchase_unit ?? null,
        requires_coc: r?.requires_coc ?? false,
        requires_heat_number: r?.requires_heat_number ?? false,
    };
}

export const PURCHASE_UNIT_LABEL: Record<PurchaseUnit, string> = {
    STOCK: "Stock unit", BOX: "Box", LB: "Pound",
};

type Props = {
    value: ReceivingControls;
    onChange: (next: ReceivingControls) => void;
    /** The item's stock unit (EA, FT…), for the conversion's wording. */
    stockUnit?: string;
};

/**
 * How an item is bought and counted at the dock, and what paperwork its lots must have
 * before they leave receiving. Shared by the Material and Part Type forms. Everything is
 * off by default — a shop that sets none of it just books lots in.
 */
export function ReceivingControlsFields({ value, onChange, stockUnit = "EA" }: Props) {
    const set = (patch: Partial<ReceivingControls>) => onChange({ ...value, ...patch });
    const converts = value.purchase_unit !== "STOCK";
    return (
        <div className="space-y-4 rounded-md border p-4">
            <div>
                <div className="text-sm font-medium">Receiving</div>
                <p className="text-xs text-muted-foreground">
                    How it&rsquo;s counted at the dock, and what each lot must have before it
                    leaves receiving.
                </p>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                    <Label>Bought and counted by</Label>
                    <Select value={value.purchase_unit}
                        onValueChange={(v) => set({ purchase_unit: v as PurchaseUnit })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="STOCK">The stock unit ({stockUnit})</SelectItem>
                            <SelectItem value="BOX">Box</SelectItem>
                            <SelectItem value="LB">Pound (weighed)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                {converts && (
                    <div className="space-y-1.5">
                        <Label htmlFor="rc-per">
                            {stockUnit} per {value.purchase_unit === "BOX" ? "box" : "pound"}
                        </Label>
                        <Input id="rc-per" type="number" min={0} step="any"
                            placeholder={value.purchase_unit === "BOX" ? "e.g. 2000" : "e.g. 450"}
                            value={value.units_per_purchase_unit ?? ""}
                            onChange={(e) => set({ units_per_purchase_unit: e.target.value === "" ? null : e.target.value })} />
                        <p className="text-xs text-muted-foreground">
                            The clerk enters {value.purchase_unit === "BOX" ? "boxes" : "the scale reading"};
                            the lot is booked in {stockUnit}.
                        </p>
                    </div>
                )}
            </div>
            <div className="flex items-center justify-between gap-4">
                <div>
                    <Label htmlFor="rc-coc">Requires a certificate of conformance</Label>
                    <p className="text-xs text-muted-foreground">Each lot is held until its CoC is uploaded.</p>
                </div>
                <Switch id="rc-coc" checked={value.requires_coc}
                    onCheckedChange={(c) => set({ requires_coc: c })} />
            </div>
            <div className="flex items-center justify-between gap-4">
                <div>
                    <Label htmlFor="rc-heat">Requires a heat number</Label>
                    <p className="text-xs text-muted-foreground">Each lot is held until its heat / melt number is entered.</p>
                </div>
                <Switch id="rc-heat" checked={value.requires_heat_number}
                    onCheckedChange={(c) => set({ requires_heat_number: c })} />
            </div>
        </div>
    );
}
