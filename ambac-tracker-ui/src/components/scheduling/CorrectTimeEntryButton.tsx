import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";

/** A datetime-local value for an ISO time, in the browser's zone. */
const toLocal = (iso?: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

/**
 * Clock times recorded wrong — a missed clock-out, a break never ended: a lead corrects
 * them before the hours are approved, with a reason kept beside each change
 * (Corrections #5). Once approved, the entry is final.
 */
export function CorrectTimeEntryButton({ entry }: {
    entry: { id: string; user_name?: string | null; start_time: string; end_time?: string | null };
}) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [start, setStart] = useState(toLocal(entry.start_time));
    const [end, setEnd] = useState(toLocal(entry.end_time));
    const [why, setWhy] = useState("");
    const changed = start !== toLocal(entry.start_time) || end !== toLocal(entry.end_time);
    const mut = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_TimeEntries_partial_update({
            start_time: new Date(start).toISOString(),
            ...(end ? { end_time: new Date(end).toISOString() } : {}),
            edit_reason: why.trim(),
        }, { params: { id: entry.id } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "time-entries" });
            toast.success("Clock times corrected.");
            setWhy("");
            setOpen(false);
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Couldn't correct the times"),
    });
    return (
        <>
            <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>Correct times</Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Correct clock times{entry.user_name ? ` · ${entry.user_name}` : ""}</DialogTitle>
                        <DialogDescription>
                            Before the hours are approved. Each change and your reason are kept on the entry.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="cte-start">Clocked in</Label>
                            <Input id="cte-start" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="cte-end">Clocked out</Label>
                            <Input id="cte-end" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
                        </div>
                        <Textarea className="col-span-2" rows={2} value={why} onChange={(e) => setWhy(e.target.value)}
                            aria-label="Reason" placeholder="Why — e.g. forgot to clock out; left at 15:30" />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={mut.isPending}>Cancel</Button>
                        <Button onClick={() => mut.mutate()} disabled={!changed || !start || !why.trim() || mut.isPending}>
                            {mut.isPending ? "Saving…" : "Correct"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
