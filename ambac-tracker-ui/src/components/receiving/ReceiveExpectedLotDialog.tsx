import { LocationCombobox } from "@/components/locations/LocationCombobox";
import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { SOURCE_TYPE_OPTIONS, type SourceType } from "@/components/receiving/lotStatus";
import { useReceiveExpectedLot, useUploadLotCoC } from "@/hooks/useReceivingMutations";
import { useCreateDocument } from "@/hooks/useCreateDocument";
import { useContentTypeMapping } from "@/hooks/useContentTypes";

type Props = {
    lotId: string;
    /** What the material is, for the dialog title — the placeholder lot number means
     *  nothing to the person holding the box. */
    itemName: string;
    /** Quantity ordered, prefilled so a matching delivery is one click. */
    orderedQuantity?: string | null;
    unitOfMeasure?: string | null;
    /** The item's buying unit and conversion: with BOX / LB set, the clerk can count in
     *  boxes or pounds and see the stock quantity it comes to. */
    purchaseUnit?: string | null;
    unitsPerPurchaseUnit?: string | null;
    /** The item holds lots until their heat number is entered — say so up front. */
    requiresHeatNumber?: boolean;
    /** Jump to the receiving-inspection screen for this lot. Offered only when routing
     *  actually parked the lot for a disposition — a dock-to-stock lot has nothing to
     *  inspect, and a dead link there is worse than no link. */
    onInspect?: (lotId: string) => void;
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

/** Statuses that mean "someone still has to make a call on this lot". */
const NEEDS_DISPOSITION = ["RECEIVED", "AWAITING_INSPECTION", "QUARANTINE"];

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Book in an expected receipt that has physically arrived.
 *
 * Two things get corrected at this moment and nowhere else: the supplier's real lot
 * number replaces the generated placeholder, and the quantity becomes what actually
 * turned up. Short shipments and overages are normal, so the quantity is editable
 * rather than assumed.
 *
 * The lot lands at RECEIVED and is then routed like any other delivery — to incoming
 * inspection, or straight to stock when the material has no receiving step. Which of
 * those happens is the routing rule's call, so the copy here doesn't promise either.
 */
export function ReceiveExpectedLotDialog({
    lotId,
    itemName,
    orderedQuantity,
    unitOfMeasure,
    purchaseUnit,
    unitsPerPurchaseUnit,
    requiresHeatNumber = false,
    onInspect,
    open,
    onOpenChange,
}: Props) {
    const [lotNumber, setLotNumber] = useState("");
    const [quantity, setQuantity] = useState(orderedQuantity ?? "");
    const [receivedDate, setReceivedDate] = useState(today());
    const [location, setLocation] = useState("");
    // A short delivery: the clerk says, from the packing slip, whether more is coming.
    const [remainder, setRemainder] = useState<"BACKORDERED" | "CLOSED" | "">("");
    const [acceptOverage, setAcceptOverage] = useState(false);
    const [heatNumber, setHeatNumber] = useState("");
    const [sourceType, setSourceType] = useState<SourceType | "">("");
    // The cert, photographed at the dock (or a PDF) — uploaded onto the lot once it's
    // received, which clears an "awaiting CoC" hold by itself.
    const [cocFile, setCocFile] = useState<File | null>(null);
    const uploadCoc = useUploadLotCoC();
    // The supplier's packing slip, filed with the lot's documents — the paper the
    // delivery came with, kept beside the receipt it backs.
    const [slipFile, setSlipFile] = useState<File | null>(null);
    const createDocument = useCreateDocument();
    const { getContentTypeId } = useContentTypeMapping();
    // Counting in the buying unit ("3 boxes") when the item has one with a conversion.
    const buyingUnit: "BOX" | "LB" | null =
        purchaseUnit === "BOX" || purchaseUnit === "LB" ? purchaseUnit : null;
    const factor = buyingUnit && unitsPerPurchaseUnit ? Number(unitsPerPurchaseUnit) : 0;
    const [countIn, setCountIn] = useState<"STOCK" | "BOX" | "LB">("STOCK");
    const [counted, setCounted] = useState("");
    const receive = useReceiveExpectedLot();

    const reset = () => {
        setLotNumber("");
        setQuantity(orderedQuantity ?? "");
        setReceivedDate(today());
        setLocation("");
        setRemainder("");
        setHeatNumber("");
        setSourceType("");
        setAcceptOverage(false);
        setCountIn("STOCK");
        setCounted("");
        setCocFile(null);
        setSlipFile(null);
    };

    // In the buying unit, the stock quantity follows from the count.
    const inBuyingUnit = countIn !== "STOCK" && factor > 0;
    const effectiveQty = inBuyingUnit
        ? (counted !== "" && Number(counted) > 0 ? String(Number(counted) * factor) : "")
        : quantity;

    const qtyValid = effectiveQty !== "" && Number(effectiveQty) > 0;
    const short = qtyValid && orderedQuantity != null && Number(effectiveQty) !== Number(orderedQuantity);
    /** How many fewer arrived than were on order (negative for an overage). */
    const shortBy = qtyValid && orderedQuantity != null ? Number(orderedQuantity) - Number(effectiveQty) : 0;
    const canSubmit = qtyValid && receivedDate !== "" && !receive.isPending
        && (shortBy <= 0 || remainder !== "");

    const submit = () => {
        if (!canSubmit) return;
        receive.mutate(
            {
                id: lotId,
                supplier_lot_number: lotNumber.trim(),
                quantity: effectiveQty,
                received_date: receivedDate,
                storage_location: location,
                ...(shortBy > 0 && remainder ? { remainder } : {}),
                ...(shortBy < 0 && acceptOverage ? { accept_overage: true } : {}),
                ...(inBuyingUnit && buyingUnit ? { received_as_quantity: counted, received_as_unit: buyingUnit } : {}),
                ...(heatNumber.trim() ? { heat_number: heatNumber.trim() } : {}),
                ...(sourceType ? { source_type: sourceType } : {}),
            },
            {
                onSuccess: (data: unknown) => {
                    // The response is the lot *after* routing ran, so it says where the
                    // lot actually went — inspection, a soft hold, or straight to stock.
                    const { status, lot_number: ours } = (data as { status?: string; lot_number?: string }) ?? {};
                    const parked = status != null && NEEDS_DISPOSITION.includes(status);
                    const lotCt = getContentTypeId("materiallot");
                    if (slipFile && lotCt) {
                        createDocument.mutate({
                            file: slipFile, file_name: `Packing slip · ${ours ?? ""}`.trim(),
                            content_type: lotCt, object_id: lotId, classification: "INTERNAL" as const,
                        }, {
                            onError: () => toast.error(`Lot ${ours} was received, but the packing slip didn't upload — add it from the lot.`),
                        });
                    }
                    if (cocFile) {
                        uploadCoc.mutate({ id: lotId, file: cocFile }, {
                            onSuccess: () => toast.success(`CoC attached to lot ${ours}.`),
                            onError: () => toast.error(`Lot ${ours} was received, but the CoC didn't upload — add it from the lot.`),
                        });
                    }
                    toast.success(
                        parked
                            ? `Lot ${ours} received — waiting on incoming inspection.`
                            : `Lot ${ours} received and available.`,
                        parked && onInspect
                            ? { action: { label: "Inspect", onClick: () => onInspect(lotId) } }
                            : undefined,
                    );
                    reset();
                    onOpenChange(false);
                },
                onError: (err: unknown) => {
                    const detail =
                        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                    toast.error(detail ?? "Could not receive the lot");
                },
            },
        );
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(o) => {
                if (!o) reset();
                onOpenChange(o);
            }}
        >
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Receive · {itemName}</DialogTitle>
                    <DialogDescription>
                        Book in the delivery. The lot is then routed the same way any receipt
                        is &mdash; to incoming inspection, or straight to stock if this
                        material doesn&rsquo;t need one.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="rel-lot">Supplier lot number</Label>
                        <Input
                            id="rel-lot"
                            className="font-mono"
                            placeholder="As printed on the packing slip / label"
                            value={lotNumber}
                            onChange={(e) => setLotNumber(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            Kept for traceability. The lot gets its own number when it&rsquo;s booked in.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="rel-qty">
                                {inBuyingUnit
                                    ? `${countIn === "BOX" ? "Boxes" : "Weight (lb)"} received`
                                    : `Quantity received${unitOfMeasure ? ` (${unitOfMeasure})` : ""}`}
                            </Label>
                            {factor > 0 && buyingUnit && (
                                <div className="flex gap-1">
                                    <Button type="button" size="sm" variant={countIn === "STOCK" ? "default" : "outline"}
                                        onClick={() => setCountIn("STOCK")}>{unitOfMeasure || "Count"}</Button>
                                    <Button type="button" size="sm" variant={countIn !== "STOCK" ? "default" : "outline"}
                                        onClick={() => setCountIn(buyingUnit)}>{buyingUnit === "BOX" ? "Boxes" : "Weigh"}</Button>
                                </div>
                            )}
                            {inBuyingUnit ? (
                                <>
                                    <Input id="rel-qty" type="number" min="0" step="any"
                                        value={counted} onChange={(e) => setCounted(e.target.value)} />
                                    {effectiveQty && (
                                        <p className="text-xs text-muted-foreground">
                                            = {effectiveQty} {unitOfMeasure ?? ""} at {unitsPerPurchaseUnit} per {countIn === "BOX" ? "box" : "lb"}
                                        </p>
                                    )}
                                </>
                            ) : (
                                <Input
                                    id="rel-qty"
                                    type="number"
                                    min="0"
                                    step="any"
                                    value={quantity}
                                    onChange={(e) => setQuantity(e.target.value)}
                                />
                            )}
                            {short && shortBy < 0 && (
                                <p className="text-xs text-amber-600">
                                    Ordered {orderedQuantity} — booking in what actually arrived.
                                </p>
                            )}
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="rel-date">Received</Label>
                            <Input
                                id="rel-date"
                                type="date"
                                value={receivedDate}
                                onChange={(e) => setReceivedDate(e.target.value)}
                            />
                        </div>
                    </div>
                    {shortBy < 0 && (
                        <label className="flex items-start gap-2 rounded-md border border-sky-300 bg-sky-50/50 p-3 text-sm dark:bg-sky-950/20">
                            <input type="checkbox" className="mt-1" checked={acceptOverage}
                                onChange={(e) => setAcceptOverage(e.target.checked)} />
                            <span>
                                <span className="font-medium">{-shortBy} more than the {orderedQuantity} ordered.</span>{" "}
                                Accept the overage — needed when it&rsquo;s beyond the tolerance your organization set.
                            </span>
                        </label>
                    )}
                    {shortBy > 0 && (
                        <fieldset className="space-y-2 rounded-md border border-amber-300 bg-amber-50/50 p-3 dark:bg-amber-950/20">
                            <legend className="px-1 text-sm font-medium">
                                {shortBy} fewer than the {orderedQuantity} on order. What does the packing slip say?
                            </legend>
                            <label className="flex items-start gap-2 text-sm">
                                <input type="radio" name="rel-remainder" className="mt-1" checked={remainder === "BACKORDERED"}
                                    onChange={() => setRemainder("BACKORDERED")} />
                                <span><span className="font-medium">More coming</span> — keep the other {shortBy} on
                                    order, same supplier, PO and promised date.</span>
                            </label>
                            <label className="flex items-start gap-2 text-sm">
                                <input type="radio" name="rel-remainder" className="mt-1" checked={remainder === "CLOSED"}
                                    onChange={() => setRemainder("CLOSED")} />
                                <span><span className="font-medium">That&rsquo;s all</span> — nothing more is expected on
                                    this line. (UQMES stops planning on the rest; closing the PO line is
                                    done in the ERP.)</span>
                            </label>
                        </fieldset>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="rel-heat">
                                Heat number{" "}
                                <span className="text-muted-foreground">{requiresHeatNumber ? "(required)" : "(optional)"}</span>
                            </Label>
                            <Input id="rel-heat" className="font-mono" value={heatNumber}
                                onChange={(e) => setHeatNumber(e.target.value)} />
                            {requiresHeatNumber && !heatNumber.trim() && (
                                <p className="text-xs text-amber-600">Without it the lot is held until it&rsquo;s entered.</p>
                            )}
                        </div>
                        <div className="space-y-1.5">
                            <Label>Source <span className="text-muted-foreground">(from the paperwork, if shown)</span></Label>
                            <Select value={sourceType} onValueChange={(v) => setSourceType(v as SourceType)}>
                                <SelectTrigger aria-label="Source"><SelectValue placeholder="Optional" /></SelectTrigger>
                                <SelectContent>
                                    {SOURCE_TYPE_OPTIONS.map((o) => (
                                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rel-coc">Certificate of Conformance <span className="text-muted-foreground">(optional — photo or PDF)</span></Label>
                        <Input id="rel-coc" type="file" accept="image/*,application/pdf" capture="environment"
                            onChange={(e) => setCocFile(e.target.files?.[0] ?? null)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rel-slip">Packing slip <span className="text-muted-foreground">(optional — photo or PDF)</span></Label>
                        <Input id="rel-slip" type="file" accept="image/*,application/pdf" capture="environment"
                            onChange={(e) => setSlipFile(e.target.files?.[0] ?? null)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rel-location">Put away at</Label>
                        <LocationCombobox id="rel-location" value={location} onChange={(v) => setLocation(v ?? "")}
                            placeholder="Optional — the receiving dock if none" />
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={receive.isPending}
                    >
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        {receive.isPending ? "Receiving…" : "Receive lot"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
