import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { CircleAlert } from "lucide-react";
import { api, schemas } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { matchKey } from "@/lib/query-filters";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";
import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes";
import type { ExceptionItem } from "./mockData";

type DowntimeCategory = (typeof schemas.DowntimeCategoryEnum.options)[number];

const CATEGORY_LABELS: Record<DowntimeCategory, string> = {
    PLANNED: "Planned maintenance",
    UNPLANNED: "Unplanned / breakdown",
    CHANGEOVER: "Changeover / setup",
    CALIBRATION: "Calibration",
    NO_WORK: "No work available",
    NO_OPERATOR: "No operator available",
    MATERIAL: "Waiting for material",
    QUALITY: "Quality issue",
    OTHER: "Other",
};

const NO_WORK_ORDER = "__none__";

type Props = {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    /** If provided, downtime is recorded against this WO and the WO picker is hidden */
    scopedWorkOrderId?: string;
    scopedWorkOrderErpId?: string;
    /** Offered as an optional link when the dialog is not scoped to one WO */
    workOrders?: { id: string; erp_id: string }[];
};

export function ReportExceptionDialog({
    open,
    onOpenChange,
    scopedWorkOrderId,
    scopedWorkOrderErpId,
    workOrders = [],
}: Props) {
    const [kind, setKind] = useState<ExceptionItem["kind"]>("DOWNTIME");
    const [equipmentId, setEquipmentId] = useState("");
    const [category, setCategory] = useState<DowntimeCategory>("UNPLANNED");
    const [reason, setReason] = useState("");
    const [description, setDescription] = useState("");
    const [workOrderId, setWorkOrderId] = useState(NO_WORK_ORDER);

    useEffect(() => {
        if (!open) return;
        setKind("DOWNTIME");
        setEquipmentId("");
        setCategory("UNPLANNED");
        setReason("");
        setDescription("");
        setWorkOrderId(NO_WORK_ORDER);
    }, [open]);

    const { data: equipmentData } = useRetrieveEquipments({ limit: 500 }, undefined, { enabled: open });
    const { data: typeData } = useRetrieveEquipmentTypes({ limit: 500 }, undefined, { enabled: open });

    // A type with Track downtime off is not a production resource (handhelds, torque
    // tools) and the server refuses downtime against it. Equipment with no type is tracked.
    const equipment = useMemo(() => {
        const untracked = new Set(
            (typeData?.results ?? []).filter((t) => t.track_downtime === false).map((t) => t.id),
        );
        return (equipmentData?.results ?? [])
            .filter((e) => !e.equipment_type || !untracked.has(e.equipment_type))
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [equipmentData, typeData]);

    const queryClient = useQueryClient();
    const recordDowntime = useMutation({
        mutationFn: () =>
            api.api_DowntimeEvents_create(
                {
                    equipment: equipmentId,
                    category,
                    reason: reason.trim(),
                    description: description.trim(),
                    start_time: new Date().toISOString(),
                    work_order: scopedWorkOrderId ?? (workOrderId === NO_WORK_ORDER ? null : workOrderId),
                },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries(matchKey(["downtime-events"]));
            toast.success("Downtime recorded");
            onOpenChange(false);
        },
        onError: (err) => toast.error(apiErrorMessage(err) ?? "Could not record downtime"),
    });

    const canSubmit = !!equipmentId && reason.trim().length > 0 && !recordDowntime.isPending;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <CircleAlert className="h-4 w-4" />
                        Report exception
                    </DialogTitle>
                    <DialogDescription>
                        Records an event that blocks or risks production. Downtime is recorded here;
                        a quarantine or a CAPA is raised on its own form.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-3">
                    <div className="space-y-1">
                        <Label>Type</Label>
                        <Select value={kind} onValueChange={(v) => setKind(v as ExceptionItem["kind"])}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="DOWNTIME">Downtime (equipment / resource)</SelectItem>
                                <SelectItem value="QUARANTINE">Quarantine (quality hold)</SelectItem>
                                <SelectItem value="CAPA">CAPA (corrective action)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {kind === "DOWNTIME" ? (
                        <>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <Label>Equipment</Label>
                                    <Select value={equipmentId} onValueChange={setEquipmentId}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Choose a machine" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {equipment.map((e) => (
                                                <SelectItem key={e.id} value={e.id}>
                                                    {e.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <Label>Category</Label>
                                    <Select value={category} onValueChange={(v) => setCategory(v as DowntimeCategory)}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {schemas.DowntimeCategoryEnum.options.map((c) => (
                                                <SelectItem key={c} value={c}>
                                                    {CATEGORY_LABELS[c]}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="space-y-1">
                                <Label htmlFor="exc-reason">Reason</Label>
                                <Input
                                    id="exc-reason"
                                    value={reason}
                                    maxLength={200}
                                    onChange={(e) => setReason(e.target.value)}
                                    placeholder="e.g. Spindle runout out of spec"
                                />
                            </div>
                            <div className="space-y-1">
                                <Label htmlFor="exc-desc">Description</Label>
                                <Textarea
                                    id="exc-desc"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="min-h-[80px]"
                                />
                            </div>

                            {scopedWorkOrderErpId ? (
                                <div className="rounded-md border bg-muted/30 p-2 text-xs text-muted-foreground">
                                    Recorded against <span className="font-mono">{scopedWorkOrderErpId}</span>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    <Label>Work order</Label>
                                    <Select value={workOrderId} onValueChange={setWorkOrderId}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value={NO_WORK_ORDER}>None</SelectItem>
                                            {workOrders.map((w) => (
                                                <SelectItem key={w.id} value={w.id}>
                                                    {w.erp_id}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <p className="text-xs text-muted-foreground">
                                        The work order the machine was running, if any.
                                    </p>
                                </div>
                            )}
                            <p className="text-xs text-muted-foreground">
                                Starts now. Resolve it from the exceptions list when the machine is back.
                            </p>
                        </>
                    ) : kind === "QUARANTINE" ? (
                        <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                            A quarantine holds a specific part and needs its own record.{" "}
                            <Link to="/production/dispositions/new" className="text-primary hover:underline">
                                Open the disposition form
                            </Link>
                            .
                        </p>
                    ) : (
                        <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                            A CAPA needs a problem statement, an owner and an investigation.{" "}
                            <Link to="/quality/capas/new" className="text-primary hover:underline">
                                Open the CAPA form
                            </Link>
                            .
                        </p>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    {kind === "DOWNTIME" && (
                        <Button onClick={() => recordDowntime.mutate()} disabled={!canSubmit}>
                            Record downtime
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
