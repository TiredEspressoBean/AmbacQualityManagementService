import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, schemas } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";

type DowntimeCategory = (typeof schemas.DowntimeCategoryEnum.options)[number];

const CATEGORIES: Record<DowntimeCategory, string> = {
    PLANNED: "Planned maintenance", UNPLANNED: "Unplanned / breakdown", CHANGEOVER: "Changeover / setup",
    CALIBRATION: "Calibration", NO_WORK: "No work available", NO_OPERATOR: "No operator available",
    MATERIAL: "Waiting for material", QUALITY: "Quality issue", OTHER: "Other",
};

/** A datetime-local value for an ISO time, in the browser's zone. */
const toLocal = (iso?: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

/**
 * A downtime event recorded wrong — the wrong machine, the wrong times, the wrong
 * reason: correct it, with a reason. Each change and the reason are kept on the event
 * (Corrections #13).
 */
export function CorrectDowntimeDialog({ eventId, open, onOpenChange }: {
    eventId: string; open: boolean; onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const { data: event } = useQuery({
        queryKey: ["downtime-event", eventId],
        queryFn: () => api.api_DowntimeEvents_retrieve({ params: { id: eventId } }),
        enabled: open,
    });
    const { data: equipment } = useRetrieveEquipments({ limit: 500 }, undefined, { enabled: open });
    const [machine, setMachine] = useState("");
    const [category, setCategory] = useState<DowntimeCategory>("UNPLANNED");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [what, setWhat] = useState("");
    const [why, setWhy] = useState("");
    useEffect(() => {
        if (!event) return;
        setMachine(event.equipment ? String(event.equipment) : "");
        setCategory(event.category as DowntimeCategory);
        setStart(toLocal(event.start_time));
        setEnd(toLocal(event.end_time));
        setWhat(event.reason ?? "");
    }, [event]);

    const mut = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_DowntimeEvents_partial_update({
            ...(machine ? { equipment: machine } : {}),
            category, reason: what,
            start_time: new Date(start).toISOString(),
            ...(end ? { end_time: new Date(end).toISOString() } : {}),
            edit_reason: why.trim(),
        }, { params: { id: eventId } }),
        onSuccess: () => {
            queryClient.invalidateQueries();
            toast.success("Downtime corrected.");
            setWhy("");
            onOpenChange(false);
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Couldn't correct the downtime"),
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Correct downtime</DialogTitle>
                    <DialogDescription>
                        Recorded wrong — the machine, times or reason. Each change and your reason are kept on the event.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2 space-y-1.5">
                        <Label>Machine</Label>
                        <Select value={machine || undefined} onValueChange={setMachine}>
                            <SelectTrigger><SelectValue placeholder="Machine" /></SelectTrigger>
                            <SelectContent>
                                {(equipment?.results ?? []).map((e) => (
                                    <SelectItem key={String(e.id)} value={String(e.id)}>{e.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="col-span-2 space-y-1.5">
                        <Label>Category</Label>
                        <Select value={category} onValueChange={(v) => setCategory(v as DowntimeCategory)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {Object.entries(CATEGORIES).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="cd-start">Started</Label>
                        <Input id="cd-start" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="cd-end">Ended</Label>
                        <Input id="cd-end" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
                    </div>
                    <div className="col-span-2 space-y-1.5">
                        <Label htmlFor="cd-what">What happened</Label>
                        <Input id="cd-what" value={what} onChange={(e) => setWhat(e.target.value)} />
                    </div>
                    <Textarea className="col-span-2" rows={2} value={why} onChange={(e) => setWhy(e.target.value)}
                        aria-label="Reason for the correction" placeholder="Why — e.g. logged on Lathe 1, it was Lathe 2" />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mut.isPending}>Cancel</Button>
                    <Button onClick={() => mut.mutate()} disabled={!event || !start || !why.trim() || mut.isPending}>
                        {mut.isPending ? "Saving…" : "Correct"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
