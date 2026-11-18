import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api/generated";
import { invalidateAfterNcrChange } from "@/hooks/ncrs";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export type CombinableNcr = { id: string; ncr_number: string; created_at: string; description?: string | null };

/** Combine NCRs into one (services/qms/ncr.combine_ncrs). The target — the oldest by
 *  default — keeps its header; the others' decisions and records move under it, and each
 *  closes as combined into it. Used from the NCR list and the Dispositions list. */
export function CombineNcrsDialog({ ncrs, open, onOpenChange, onDone }: {
    ncrs: CombinableNcr[]; open: boolean; onOpenChange: (o: boolean) => void; onDone?: () => void;
}) {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const sorted = [...ncrs].sort((a, b) => a.created_at.localeCompare(b.created_at));
    const [into, setInto] = useState<string>(sorted[0]?.id ?? "");
    useEffect(() => { if (open) setInto(sorted[0]?.id ?? ""); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

    const combine = useMutation({
        mutationFn: () => api.api_NCRs_combine_create({ into, ncrs: ncrs.map((n) => n.id).filter((id) => id !== into) }),
        meta: { errorMessage: "Couldn't combine the NCRs", successMessage: "NCRs combined" },
        onSuccess: (ncr) => {
            void invalidateAfterNcrChange(queryClient);
            onOpenChange(false);
            onDone?.();
            navigate({ to: "/quality/ncrs/$ncrId", params: { ncrId: String(ncr.id) } });
        },
    });

    const target = sorted.find((n) => n.id === into);
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Combine {ncrs.length} NCRs into one</DialogTitle>
                    <DialogDescription>
                        The others' decisions and inspection records move under the one you keep, and each of them
                        closes as combined into it. The one you keep keeps what's wrong; its severity becomes the
                        group's highest, and the others' containment is added to its own.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-2">
                    <Label>Keep</Label>
                    <RadioGroup value={into} onValueChange={setInto} className="space-y-1">
                        {sorted.map((n) => (
                            <div key={n.id} className="flex items-start gap-2">
                                <RadioGroupItem value={n.id} id={`combine-into-${n.id}`} className="mt-0.5" />
                                <Label htmlFor={`combine-into-${n.id}`} className="font-normal">
                                    <span className="font-mono">{n.ncr_number}</span>
                                    {n.description && <span className="text-muted-foreground"> — {n.description}</span>}
                                </Label>
                            </div>
                        ))}
                    </RadioGroup>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button disabled={!into || ncrs.length < 2 || combine.isPending} onClick={() => combine.mutate()}>
                        {combine.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Combine into {target?.ncr_number ?? "one NCR"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
