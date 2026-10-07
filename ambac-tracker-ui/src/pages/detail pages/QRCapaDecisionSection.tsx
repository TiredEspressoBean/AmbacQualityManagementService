import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { api } from "@/lib/api/generated";
import { QRMeasurementsSection } from "./QRMeasurementsSection";

const LABEL: Record<string, string> = {
    PROMOTED: "CAPA raised",
    NOT_REQUIRED: "No CAPA needed",
    DEFERRED: "Deferred",
};

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string; note?: string[] } } })?.response?.data?.detail
    ?? (err as { response?: { data?: { note?: string[] } } })?.response?.data?.note?.[0] ?? fallback;

/**
 * Whether this failure needed a CAPA. Raising one (Create CAPA, above) marks it CAPA
 * raised; otherwise someone with the authority to raise a CAPA records No CAPA needed
 * or Deferred, with the reason. Undecided failures are listed on the NCR page.
 */
function CapaDecisionCard({ report }: { report: Record<string, unknown> }) {
    const qc = useQueryClient();
    const { has } = usePermissionSet();
    const id = String(report.id);
    const decision = (report.capa_decision as string | null) ?? null;
    const [choice, setChoice] = useState<"NOT_REQUIRED" | "DEFERRED">("NOT_REQUIRED");
    const [note, setNote] = useState("");
    const [editing, setEditing] = useState(false);
    const save = useMutation({
        mutationFn: () => api.api_QualityReports_capa_decision_create({ decision: choice, note }, { params: { id } }),
        onSuccess: () => {
            toast.success("Decision recorded.");
            setEditing(false); setNote("");
            void qc.invalidateQueries({ predicate: (q) => q.queryKey[1] === id });
            void qc.invalidateQueries({ queryKey: ["ncr-awaiting-decision"] });
        },
        onError: (e) => toast.error(errorOf(e, "Could not record the decision")),
    });
    const canDecide = has("initiate_capa") && decision !== "PROMOTED";
    const showForm = canDecide && (decision === null || editing);

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                    CAPA decision
                    {decision
                        ? <Badge variant={decision === "PROMOTED" ? "default" : "outline"}>{LABEL[decision] ?? decision}</Badge>
                        : <Badge variant="secondary">Not decided</Badge>}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
                {decision ? (
                    <div>
                        {report.capa_decision_note ? <p className="whitespace-pre-wrap">{String(report.capa_decision_note)}</p> : null}
                        <p className="text-xs text-muted-foreground">
                            {report.capa_decided_by_name ? `${report.capa_decided_by_name} · ` : ""}
                            {report.capa_decided_at ? new Date(String(report.capa_decided_at)).toLocaleString() : ""}
                        </p>
                        {canDecide && !editing && (
                            <Button size="sm" variant="outline" className="mt-2" onClick={() => setEditing(true)}>Change decision</Button>
                        )}
                    </div>
                ) : (
                    <p className="text-muted-foreground">
                        Raise a CAPA with Create CAPA, or record why one isn&rsquo;t needed. Until then this report shows
                        as awaiting a decision on the NCR page.
                    </p>
                )}
                {showForm && (
                    <div className="space-y-2 rounded-md border p-3">
                        <div className="flex flex-wrap gap-2">
                            {(["NOT_REQUIRED", "DEFERRED"] as const).map((d) => (
                                <Button key={d} size="sm" type="button" variant={choice === d ? "default" : "outline"}
                                    onClick={() => setChoice(d)}>{LABEL[d]}</Button>
                            ))}
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="capa-note">Why</Label>
                            <Textarea id="capa-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                                placeholder={choice === "NOT_REQUIRED"
                                    ? "e.g. One-off tooling chip; the disposition covers the part, no systemic cause"
                                    : "e.g. Waiting for the next lot from this supplier before deciding"} />
                        </div>
                        <div className="flex gap-2">
                            <Button size="sm" disabled={!note.trim() || save.isPending} onClick={() => save.mutate()}>
                                {save.isPending ? "Saving…" : "Record decision"}
                            </Button>
                            {editing && <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

/** The quality report page's lower section: the CAPA decision (failures only), then
 *  the measurements. */
export function QRDetailSections({ modelData }: { modelData: Record<string, unknown> }) {
    return (
        <div className="space-y-4">
            {modelData.status === "FAIL" && <CapaDecisionCard report={modelData} />}
            <QRMeasurementsSection modelData={modelData} />
        </div>
    );
}
