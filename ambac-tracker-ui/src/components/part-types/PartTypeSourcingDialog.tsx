import { useEffect, useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type Props = { partTypeId: string; open: boolean; onOpenChange: (open: boolean) => void };

const suppliersOptions = () =>
    queryOptions({
        queryKey: ["companies", "part-type-supplier-picker"] as const,
        queryFn: () => api.api_Companies_list({ queries: { limit: 500, ordering: "name", is_supplier: true } }),
    });

/**
 * A bought part's sourcing — its preferred supplier, that supplier's lead time and the
 * safety stock planning holds back. A buyer keeps these current (from the ERP) without
 * editing the part itself, and a change here doesn't make a new version of the part.
 */
export function PartTypeSourcingDialog({ partTypeId, open, onOpenChange }: Props) {
    const queryClient = useQueryClient();
    const { data: partType } = useQuery({
        queryKey: ["part-type", partTypeId, "sourcing"],
        queryFn: () => api.api_PartTypes_retrieve({ params: { id: partTypeId } }),
        enabled: open,
    });
    const { data: suppliers } = useQuery({ ...suppliersOptions(), enabled: open });
    const [supplier, setSupplier] = useState<string | null>(null);
    const [leadTime, setLeadTime] = useState("");
    const [safety, setSafety] = useState("");

    useEffect(() => {
        if (!partType) return;
        setSupplier(partType.preferred_supplier ? String(partType.preferred_supplier) : null);
        setLeadTime(partType.purchase_lead_time_days != null ? String(partType.purchase_lead_time_days) : "");
        setSafety(partType.safety_stock ?? "");
    }, [partType]);

    const save = useMutation({
        mutationFn: () => api.api_PartTypes_sourcing_partial_update(
            {
                preferred_supplier: supplier,
                purchase_lead_time_days: leadTime === "" ? null : Number(leadTime),
                safety_stock: safety === "" ? null : safety,
            },
            { params: { id: partTypeId }, headers: { "X-CSRFToken": getCookie("csrftoken") } },
        ),
        onSuccess: () => {
            toast.success(`Sourcing saved for ${partType?.name ?? "the part"}.`);
            queryClient.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).toLowerCase().includes("part") });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "schedule" && q.queryKey[1] === "requirements" });
            onOpenChange(false);
        },
        onError: (err: unknown) => {
            const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
            const first = data ? Object.values(data)[0] : null;
            toast.error(Array.isArray(first) ? String(first[0]) : "Could not save the sourcing");
        },
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Sourcing · {partType?.name ?? "…"}</DialogTitle>
                    <DialogDescription>
                        Who it&rsquo;s bought from and how long they take, as the ERP has it, and the
                        safety stock planning holds back. The part itself isn&rsquo;t changed.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label>Preferred supplier</Label>
                        <Combobox
                            value={supplier}
                            onChange={setSupplier}
                            options={(suppliers?.results ?? []).map((c) => ({ value: String(c.id), label: c.name }))}
                            placeholder="None"
                            searchPlaceholder="Search suppliers…"
                            emptyText="No supplier found."
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="src-lead">Lead time (days)</Label>
                            <Input id="src-lead" type="number" min={0} value={leadTime}
                                onChange={(e) => setLeadTime(e.target.value)} placeholder="e.g. 14" />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="src-safety">Safety stock</Label>
                            <Input id="src-safety" type="number" min={0} step="any" value={safety}
                                onChange={(e) => setSafety(e.target.value)} placeholder="None" />
                        </div>
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={save.isPending}>Cancel</Button>
                    <Button onClick={() => save.mutate()} disabled={save.isPending || !partType}>
                        {save.isPending ? "Saving…" : "Save"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
