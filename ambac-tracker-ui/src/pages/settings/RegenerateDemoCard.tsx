/**
 * Demo-tenant-only card: wipe + reseed the demo back to a known state.
 *
 * Rendered on OrganizationSettingsPage only when the current tenant's
 * slug is exactly 'demo'. The hide-on-slug check is UI-side; the
 * backend separately refuses to run on any other tenant (defense in
 * depth — hide-only is not a guardrail).
 *
 * UX: typed confirmation ("REGENERATE") to break muscle memory during
 * demos; async via Celery with status polling.
 */
import { useState } from "react";
import { Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
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
import {
    useRegenerateDemoData,
    fetchRegenerateDemoStatus,
} from "@/hooks/useRegenerateDemoData";

const CONFIRM_PHRASE = "REGENERATE";
const DEMO_SLUG = "demo";

export function RegenerateDemoCard() {
    const [open, setOpen] = useState(false);
    const [typed, setTyped] = useState("");
    const [taskId, setTaskId] = useState<string | null>(null);
    const [polling, setPolling] = useState(false);

    const regen = useRegenerateDemoData();

    const handleConfirm = async () => {
        if (typed !== CONFIRM_PHRASE) return;
        try {
            const resp = await regen.mutateAsync({ slug: DEMO_SLUG });
            setTaskId(resp.task_id);
            setTyped("");
            setOpen(false);
            toast.info("Regenerating demo tenant…", {
                description: "This wipes all demo data and reseeds the preset state.",
            });
            // Poll until terminal.
            setPolling(true);
            const start = Date.now();
            while (Date.now() - start < 5 * 60 * 1000) {
                await new Promise((r) => setTimeout(r, 2000));
                try {
                    const s = await fetchRegenerateDemoStatus(DEMO_SLUG, resp.task_id);
                    if (s.status === "SUCCESS") {
                        toast.success("Demo regenerated", {
                            description: s.result?.notes,
                        });
                        // Reload so caches and current-tenant state refresh cleanly.
                        // Otherwise the admin may see stale rows from invalidate-only.
                        window.location.reload();
                        return;
                    }
                    if (s.status === "FAILURE") {
                        toast.error(`Regeneration failed: ${s.error ?? "unknown"}`);
                        setPolling(false);
                        setTaskId(null);
                        return;
                    }
                } catch (e) {
                    console.warn("status poll failed", e);
                }
            }
            toast.warning("Regeneration is still running — refresh later to see the result.");
            setPolling(false);
        } catch (e) {
            toast.error("Could not start regeneration", {
                description: e instanceof Error ? e.message : undefined,
            });
        }
    };

    return (
        <>
            <Card className="mb-6 border-destructive/30">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2 text-destructive">
                        <RefreshCw className="h-5 w-5" />
                        Regenerate Demo Data
                    </CardTitle>
                    <CardDescription>
                        Wipe all data in the demo tenant and reseed it from the documented
                        preset state. Use this before a sales demo or training session to
                        reset to a clean, known-good fixture.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 mb-3 flex items-start gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                        <div className="text-muted-foreground">
                            <strong className="text-destructive">Destructive.</strong>{" "}
                            All work orders, parts, quality reports, training records,
                            and user data in this tenant will be deleted and replaced
                            with the seed fixture. The endpoint refuses to run on any
                            tenant other than{" "}
                            <code className="font-mono text-xs">{DEMO_SLUG}</code>.
                        </div>
                    </div>
                    <Button
                        variant="destructive"
                        onClick={() => setOpen(true)}
                        disabled={polling || regen.isPending}
                    >
                        {polling ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Regenerating…
                            </>
                        ) : (
                            <>
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Regenerate demo data
                            </>
                        )}
                    </Button>
                    {taskId && polling && (
                        <p className="mt-2 text-xs text-muted-foreground font-mono">
                            Task: {taskId}
                        </p>
                    )}
                </CardContent>
            </Card>

            <Dialog open={open} onOpenChange={(v) => !regen.isPending && setOpen(v)}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-destructive">
                            Regenerate demo tenant?
                        </DialogTitle>
                        <DialogDescription>
                            This permanently deletes all data in the demo tenant and
                            replaces it with the seed fixture. Cannot be undone.
                            Type <code className="font-mono">{CONFIRM_PHRASE}</code> to
                            confirm.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 py-2">
                        <Label htmlFor="regen-confirm" className="text-sm">
                            Confirmation
                        </Label>
                        <Input
                            id="regen-confirm"
                            value={typed}
                            onChange={(e) => setTyped(e.target.value)}
                            placeholder={CONFIRM_PHRASE}
                            autoFocus
                            autoComplete="off"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirm}
                            disabled={typed !== CONFIRM_PHRASE || regen.isPending}
                        >
                            {regen.isPending ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Queuing…
                                </>
                            ) : (
                                "Wipe and regenerate"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
