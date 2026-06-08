import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
    TooltipProvider,
} from "@/components/ui/tooltip";
import { Wrench, Trash2, X, CheckSquare, Square } from "lucide-react";
import { toast } from "sonner";

import { useStartTeardownBatch } from "@/hooks/useStartTeardownBatch";
import { useScrapCore } from "@/hooks/useScrapCore";
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses";
import { useRetrievePartType } from "@/hooks/useRetrievePartType";

export type SelectedCore = {
    id: string;
    core_number: string;
    status: string;
    core_type: string | null;
    core_type_name?: string | null;
};

type CoresBulkActionsBarProps = {
    selected: SelectedCore[];
    /**
     * Rows currently visible on the page. Used to drive "Select all on page"
     * and the corresponding deselect action.
     */
    pageItems: SelectedCore[];
    onSelectAllOnPage: () => void;
    onDeselectPage: () => void;
    onClear: () => void;
};

export function CoresBulkActionsBar({
    selected,
    pageItems,
    onSelectAllOnPage,
    onDeselectPage,
    onClear,
}: CoresBulkActionsBarProps) {
    const navigate = useNavigate();
    const [teardownOpen, setTeardownOpen] = useState(false);
    const [scrapOpen, setScrapOpen] = useState(false);
    const [scrapReason, setScrapReason] = useState("");
    const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);

    const selectedIds = useMemo(() => new Set(selected.map((c) => c.id)), [selected]);
    const selectedOnPage = useMemo(
        () => pageItems.filter((p) => selectedIds.has(p.id)).length,
        [pageItems, selectedIds],
    );
    const pageFullySelected = pageItems.length > 0 && selectedOnPage === pageItems.length;

    const allReceived = useMemo(
        () => selected.length > 0 && selected.every((c) => c.status === "RECEIVED"),
        [selected],
    );
    const sharedCoreType = useMemo(() => {
        if (selected.length === 0) return null;
        const first = selected[0]?.core_type;
        return selected.every((c) => c.core_type === first) ? first : null;
    }, [selected]);
    const sharedCoreTypeName = useMemo(() => {
        if (!sharedCoreType) return null;
        return selected[0]?.core_type_name ?? null;
    }, [selected, sharedCoreType]);

    // Fetch the core_type's default disassembly process preference.
    const { data: coreTypeData } = useRetrievePartType(
        { params: { id: sharedCoreType ?? "" } } as never,
        { enabled: teardownOpen && !!sharedCoreType },
    );
    const defaultProcessId = (coreTypeData as { default_disassembly_process?: string | null } | undefined)
        ?.default_disassembly_process ?? null;

    // Fetch eligible disassembly processes for the shared core_type.
    const { data: eligibleProcessesData, isLoading: eligibleLoading } = useRetrieveProcesses(
        sharedCoreType
            ? {
                part_type: sharedCoreType,
                is_disassembly: true,
                status: "APPROVED",
                limit: 50,
            }
            : undefined,
        undefined,
        { enabled: teardownOpen && !!sharedCoreType },
    );
    type EligibleProcess = { id: string; name: string };
    const eligibleProcesses: EligibleProcess[] = useMemo(() => {
        const results = (eligibleProcessesData as { results?: EligibleProcess[] } | undefined)?.results;
        return Array.isArray(results) ? results : [];
    }, [eligibleProcessesData]);

    // Preselect: prefer the default; fall back to the only eligible process if N=1.
    useEffect(() => {
        if (!teardownOpen) return;
        if (selectedProcessId) return;
        if (defaultProcessId && eligibleProcesses.some((p) => p.id === defaultProcessId)) {
            setSelectedProcessId(defaultProcessId);
            return;
        }
        if (eligibleProcesses.length === 1) {
            setSelectedProcessId(eligibleProcesses[0].id);
        }
    }, [teardownOpen, defaultProcessId, eligibleProcesses, selectedProcessId]);

    // Reset picker state when dialog closes.
    useEffect(() => {
        if (!teardownOpen) {
            setSelectedProcessId(null);
        }
    }, [teardownOpen]);

    const canTeardown = allReceived && !!sharedCoreType;
    const canScrap = allReceived;
    const canSubmitTeardown = canTeardown && !!selectedProcessId;

    const teardownMutation = useStartTeardownBatch();
    const scrapMutation = useScrapCore();

    function submitTeardown() {
        if (!selectedProcessId) {
            toast.error("Pick a disassembly process before submitting");
            return;
        }
        teardownMutation.mutate(
            { core_ids: selected.map((c) => c.id), process_id: selectedProcessId },
            {
                onSuccess: (data) => {
                    const wo = (data as { work_order_id?: string; work_order_erp_id?: string }) ?? {};
                    const erp = wo.work_order_erp_id ?? "teardown WO";
                    toast.success(`Started teardown batch ${erp} (${selected.length} cores)`);
                    setTeardownOpen(false);
                    onClear();
                    // Post-submit choice: navigate to the new WO so the
                    // operator can immediately work it. The cores list will
                    // re-render against the cache, which we invalidated in
                    // the hook.
                    if (wo.work_order_id) {
                        navigate({ to: `/workorder/${wo.work_order_id}/control` });
                    }
                },
                onError: (err) => {
                    toast.error(`Teardown failed: ${(err as Error).message}`);
                },
            },
        );
    }

    async function submitScrap() {
        const ids = selected.map((c) => c.id);
        const results = await Promise.allSettled(
            ids.map((id) => scrapMutation.mutateAsync({ id, reason: scrapReason })),
        );
        const failed = results.filter((r) => r.status === "rejected").length;
        if (failed === 0) {
            toast.success(`Scrapped ${ids.length} cores`);
        } else if (failed === ids.length) {
            toast.error(`All ${ids.length} scraps failed`);
        } else {
            toast.warning(`${ids.length - failed} of ${ids.length} scrapped; ${failed} failed`);
        }
        setScrapOpen(false);
        setScrapReason("");
        onClear();
    }

    // Hide entirely when there's nothing on the page AND nothing selected —
    // empty list with no pending action.
    if (selected.length === 0 && pageItems.length === 0) return null;

    return (
        <TooltipProvider>
            <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
                <Card className="border-primary shadow-lg">
                    <CardContent className="flex items-center gap-2 p-3">
                        <div className="mr-2 border-r pr-2 text-sm font-medium">
                            {selected.length} selected
                        </div>
                        {pageItems.length > 0 && (
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={pageFullySelected ? onDeselectPage : onSelectAllOnPage}
                            >
                                {pageFullySelected ? (
                                    <>
                                        <Square className="mr-1 h-4 w-4" />
                                        Deselect page
                                    </>
                                ) : (
                                    <>
                                        <CheckSquare className="mr-1 h-4 w-4" />
                                        Select all on page ({pageItems.length})
                                    </>
                                )}
                            </Button>
                        )}
                        {selected.length > 0 && (
                            <>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <span>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                disabled={!canTeardown || teardownMutation.isPending}
                                                onClick={() => setTeardownOpen(true)}
                                            >
                                                <Wrench className="mr-1 h-4 w-4" />
                                                Start Teardown Batch
                                            </Button>
                                        </span>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {canTeardown
                                            ? `Create one WO for ${selected.length} cores`
                                            : !allReceived
                                              ? "All selected cores must be RECEIVED"
                                              : "All selected cores must share the same core type"}
                                    </TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <span>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                disabled={!canScrap || scrapMutation.isPending}
                                                onClick={() => setScrapOpen(true)}
                                            >
                                                <Trash2 className="mr-1 h-4 w-4" />
                                                Bulk Scrap
                                            </Button>
                                        </span>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {canScrap ? "Scrap all selected RECEIVED cores" : "All selected cores must be RECEIVED"}
                                    </TooltipContent>
                                </Tooltip>
                                <Button size="icon" variant="ghost" onClick={onClear} aria-label="Clear selection">
                                    <X className="h-4 w-4" />
                                </Button>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>

            <Dialog open={teardownOpen} onOpenChange={setTeardownOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Start teardown batch</DialogTitle>
                        <DialogDescription>
                            Creates one work order that links {selected.length} cores
                            {sharedCoreTypeName ? ` of type "${sharedCoreTypeName}"` : ""} and
                            transitions each to IN_DISASSEMBLY.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 text-sm">
                        <div className="space-y-1.5">
                            <Label htmlFor="teardown-process">Disassembly process</Label>
                            <Select
                                value={selectedProcessId ?? ""}
                                onValueChange={(v) => setSelectedProcessId(v || null)}
                            >
                                <SelectTrigger id="teardown-process">
                                    <SelectValue
                                        placeholder={
                                            eligibleLoading
                                                ? "Loading eligible processes…"
                                                : eligibleProcesses.length === 0
                                                  ? "No eligible processes — flag a Process is_disassembly first"
                                                  : "Pick a disassembly process"
                                        }
                                    />
                                </SelectTrigger>
                                <SelectContent>
                                    {eligibleProcesses.map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.name}
                                            {p.id === defaultProcessId ? "  (default)" : ""}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {!eligibleLoading && eligibleProcesses.length === 0 && sharedCoreType && (
                                <p className="text-xs text-destructive">
                                    No APPROVED disassembly Processes are configured for this core
                                    type. An engineer must flag a Process with{" "}
                                    <code>is_disassembly=True</code> before teardown can start.
                                </p>
                            )}
                        </div>
                        <div className="space-y-1">
                            <div className="text-muted-foreground">Cores in this batch:</div>
                            <div className="max-h-40 overflow-y-auto rounded-md border bg-muted/30 p-2">
                                <ul className="space-y-0.5 font-mono text-xs">
                                    {selected.map((c) => (
                                        <li key={c.id}>{c.core_number}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setTeardownOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={submitTeardown}
                            disabled={!canSubmitTeardown || teardownMutation.isPending}
                        >
                            {teardownMutation.isPending ? "Starting…" : "Create WO and start"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={scrapOpen} onOpenChange={setScrapOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Scrap {selected.length} cores</DialogTitle>
                        <DialogDescription>
                            All selected cores will be marked SCRAPPED. This cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <Textarea
                        placeholder="Shared reason (optional)"
                        value={scrapReason}
                        onChange={(e) => setScrapReason(e.target.value)}
                        rows={3}
                    />
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setScrapOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={submitScrap} disabled={scrapMutation.isPending}>
                            {scrapMutation.isPending ? "Scrapping…" : "Scrap All"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </TooltipProvider>
    );
}