import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, FileText, Loader2, Plus } from "lucide-react";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { invalidateAfterNcrChange, useNcr } from "@/hooks/ncrs";
import { useRetrieveParts } from "@/hooks/parts";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { MultiPicker } from "@/components/ui/multi-picker";
import { Combobox } from "@/components/ui/combobox";
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader";
import { EntityDocumentsEditor } from "@/components/documents/EntityDocumentsEditor";
import { StatusBadge } from "@/components/ui/status-badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { ReportButton } from "@/components/reports/ReportButton";
import { SecondPersonCosignDialog } from "@/components/second-person-cosign-dialog";
import { ReasonPromptDialog } from "@/components/change-control/ReasonPromptDialog";
import type { Schema } from "@/lib/api/types";

type Ncr = Schema<"NCR">;
type DispositionType = "REWORK" | "REPAIR" | "SCRAP" | "USE_AS_IS" | "RETURN_TO_SUPPLIER" | "NOT_NONCONFORMANCE";

const DECISIONS: { value: DispositionType; label: string }[] = [
    { value: "REWORK", label: "Rework" },
    { value: "REPAIR", label: "Repair (AS9100)" },
    { value: "SCRAP", label: "Scrap" },
    { value: "USE_AS_IS", label: "Use As Is" },
    { value: "RETURN_TO_SUPPLIER", label: "Return to Supplier" },
];
const decisionLabel = (t: string | null | undefined) =>
    t ? (DECISIONS.find((d) => d.value === t)?.label
        ?? (t === "NOT_NONCONFORMANCE" ? "Not a nonconformance" : t)) : null;

const SEVERITIES = [
    { value: "CRITICAL", label: "Critical - Safety/Regulatory Impact" },
    { value: "MAJOR", label: "Major - Functional Impact" },
    { value: "MINOR", label: "Minor - Cosmetic Only" },
] as const;

const CAPA_LABEL: Record<string, string> = {
    PROMOTED: "CAPA raised", NOT_REQUIRED: "No CAPA needed", DEFERRED: "Deferred",
};

export function NcrDetailPage() {
    const { ncrId } = useParams({ strict: false }) as { ncrId: string };
    const { data: ncr, isLoading, isError } = useNcr(ncrId);

    if (isError) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <p className="text-sm text-destructive">Couldn't load this NCR. It may not exist, or you may not have access to it.</p>
            </div>
        );
    }
    if (isLoading || !ncr) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                <p className="text-sm text-muted-foreground">Loading NCR...</p>
            </div>
        );
    }
    return <NcrDetail ncr={ncr} />;
}

function NcrDetail({ ncr }: { ncr: Ncr }) {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const perms = usePermissionSet();
    const open = ncr.state === "OPEN";
    // Raising and adding parts is anyone's who can flag a problem; the header and
    // containment are the leads' and QA's (user ruling 2026-11-17).
    const canEdit = perms.has("change_ncr") && open;
    const canAdd = perms.has("add_ncr") && open;
    const refresh = () => { void invalidateAfterNcrChange(queryClient); };

    return (
        <div className="container space-y-6 py-8 px-4 md:px-6">
            <div className="flex flex-wrap items-center gap-3">
                <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/quality/ncrs" })}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    NCRs
                </Button>
                <h1 className="text-xl font-semibold font-mono">{ncr.ncr_number}</h1>
                <StatusBadge status={ncr.state} label={ncr.state_display} />
                <StatusBadge status={ncr.severity} label={ncr.severity_display} />
                <div className="ml-auto flex items-center gap-2">
                    <ReportButton reportType="ncr_report" label="NCR Report" params={{ id: String(ncr.id) }} />
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                <div className="space-y-6 lg:col-span-2">
                    <MembersCard ncr={ncr} onChanged={refresh} canAdd={canAdd} />
                    <HeaderCard ncr={ncr} canEdit={canEdit} onChanged={refresh} />
                    <ContainmentCard ncr={ncr} canEdit={canEdit} onChanged={refresh} />
                </div>
                <div className="space-y-6">
                    <FoundCard ncr={ncr} />
                    <CapaCard ncr={ncr} onChanged={refresh} />
                    <ReportsCard ncr={ncr} />
                    <DocumentsCard ncr={ncr} />
                </div>
            </div>
        </div>
    );
}

// ---- What it covers, and the decisions ------------------------------------------

function MembersCard({ ncr, onChanged, canAdd }: { ncr: Ncr; onChanged: () => void; canAdd: boolean }) {
    const waiting = ncr.members.filter((m) => m.awaiting_decision && m.part_id);
    const [chosen, setChosen] = useState<string[]>([]);
    const [decideOpen, setDecideOpen] = useState(false);
    const [addOpen, setAddOpen] = useState(false);
    const canDecide = ncr.state === "OPEN" && waiting.length > 0;
    // Only parts still waiting can be chosen — drop any decided since they were ticked.
    const chosenWaiting = chosen.filter((id) => waiting.some((m) => String(m.part_id) === id));
    const toggle = (id: string, on: boolean) =>
        setChosen((prev) => on ? [...prev, id] : prev.filter((x) => x !== id));

    return (
        <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
                <div className="space-y-1.5">
                    <CardTitle>Parts and decisions</CardTitle>
                    <CardDescription>
                        Each part's decision is its own disposition. Decide them together or a few at a time;
                        the NCR closes when every decision under it is closed.
                    </CardDescription>
                </div>
                <div className="flex shrink-0 gap-2">
                    {canAdd && (
                        <Button size="sm" variant="outline" onClick={() => setAddOpen(true)}>
                            <Plus className="mr-1 h-4 w-4" /> Add parts
                        </Button>
                    )}
                    {canDecide && (
                        <Button size="sm" onClick={() => setDecideOpen(true)}>
                            {chosenWaiting.length
                                ? `Decide ${chosenWaiting.length} chosen`
                                : `Decide all waiting (${waiting.length})`}
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {ncr.members.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nothing has been put up for a decision yet.</p>
                ) : (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-muted-foreground">
                                <th className="w-8 py-2" aria-label="Choose" />
                                <th className="py-2">Part / Lot</th>
                                <th className="py-2">Part status</th>
                                <th className="py-2">Disposition</th>
                                <th className="py-2">Decision</th>
                                <th className="py-2">State</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ncr.members.map((m) => {
                                const id = m.part_id ? String(m.part_id) : null;
                                const choosable = m.awaiting_decision && !!id && ncr.state === "OPEN";
                                return (
                                    <tr key={String(m.disposition_id ?? m.part_id ?? m.material_lot_id)} className="border-b last:border-0">
                                        <td className="py-2">
                                            {choosable && (
                                                <Checkbox
                                                    aria-label={`Choose ${m.erp_id}`}
                                                    checked={chosenWaiting.includes(id!)}
                                                    onCheckedChange={(on) => toggle(id!, on === true)}
                                                />
                                            )}
                                        </td>
                                        <td className="py-2">
                                            <span className="font-mono">{m.erp_id ?? (m.lot_number ? `Lot ${m.lot_number}` : "—")}</span>
                                            {/* A failed load's part that had left the step: not held,
                                                and any decision on it is for the record. */}
                                            {!m.held && (
                                                <span className="block text-xs text-muted-foreground">Already past the step</span>
                                            )}
                                        </td>
                                        <td className="py-2">
                                            {m.part_status
                                                ? <Badge variant={m.part_status === "QUARANTINED" ? "destructive" : "outline"}>
                                                    {m.part_status.replace(/_/g, " ")}
                                                </Badge>
                                                : <span className="text-muted-foreground">—</span>}
                                        </td>
                                        <td className="py-2">
                                            {m.disposition_id ? (
                                                <Link to="/production/dispositions/$id/edit"
                                                      params={{ id: String(m.disposition_id) }}
                                                      className="font-mono text-primary underline-offset-2 hover:underline">
                                                    {m.disposition_number}
                                                </Link>
                                            ) : <span className="text-muted-foreground">
                                                —
                                            </span>}
                                        </td>
                                        <td className="py-2">
                                            {decisionLabel(m.disposition_type)
                                                ?? (m.awaiting_decision
                                                    ? <span className="text-amber-600 dark:text-amber-400">Awaiting decision</span>
                                                    : <span className="text-muted-foreground">—</span>)}
                                        </td>
                                        <td className="py-2">
                                            {m.current_state
                                                ? <StatusBadge status={m.current_state} label={m.current_state.replace(/_/g, " ")} />
                                                : <span className="text-muted-foreground">—</span>}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </CardContent>
            <DecideDialog
                ncr={ncr}
                open={decideOpen}
                onOpenChange={setDecideOpen}
                parts={chosenWaiting.length ? chosenWaiting : null}
                count={chosenWaiting.length || waiting.length}
                onDone={() => { setChosen([]); onChanged(); }}
            />
            {/* Mounted only while open: its picker loads parts. */}
            {addOpen && <AddPartsDialog ncr={ncr} open={addOpen} onOpenChange={setAddOpen} onDone={onChanged} />}
        </Card>
    );
}

function DecideDialog({ ncr, open, onOpenChange, parts, count, onDone }: {
    ncr: Ncr; open: boolean; onOpenChange: (o: boolean) => void;
    parts: string[] | null; count: number; onDone: () => void;
}) {
    const canApprove = usePermissionSet().has("approve_disposition");
    const [type, setType] = useState<DispositionType | "">("");
    const [notes, setNotes] = useState("");
    const [reference, setReference] = useState("");
    const [cosignOpen, setCosignOpen] = useState(false);
    const [cosignError, setCosignError] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const concession = type === "USE_AS_IS" || type === "REPAIR";

    useEffect(() => {
        if (open) { setType(""); setNotes(""); setReference(""); setError(null); }
    }, [open]);

    const decide = useMutation({
        mutationFn: (cosign?: { email: string; password: string }) => api.api_NCRs_decide_create({
            disposition_type: type as DispositionType,
            ...(notes.trim() ? { notes: notes.trim() } : {}),
            ...(concession && reference.trim() ? { customer_approval_reference: reference.trim() } : {}),
            ...(parts ? { parts } : {}),
            ...(cosign ? { cosign_email: cosign.email, cosign_password: cosign.password } : {}),
        }, { params: { id: String(ncr.id) } }),
        // Refusals show in the dialog that asked, where the person can fix them.
        meta: { suppressGlobalError: true, successMessage: "Decision recorded" },
        onSuccess: () => { setCosignOpen(false); onOpenChange(false); onDone(); },
        onError: (err) => {
            const msg = apiErrorMessage(err) ?? "Couldn't record the decision";
            if (cosignOpen) setCosignError(msg); else setError(msg);
        },
    });

    const submit = () => {
        if (!type) return;
        if (!canApprove) { setCosignError(null); setCosignOpen(true); return; }
        decide.mutate(undefined);
    };

    return (
        <>
            <Dialog open={open && !cosignOpen} onOpenChange={onOpenChange}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Decide {parts ? `${count} chosen part${count === 1 ? "" : "s"}` : `all ${count} waiting`}</DialogTitle>
                        <DialogDescription>
                            Each part's decision goes on its own disposition under {ncr.ncr_number}, with you
                            (or a co-signer) as who authorized it.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Decision</Label>
                            <Select value={type} onValueChange={(v) => v && setType(v as DispositionType)}>
                                <SelectTrigger><SelectValue placeholder="Choose the decision" /></SelectTrigger>
                                <SelectContent>
                                    {DECISIONS.map((d) => <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        {concession && (
                            <div className="space-y-2">
                                <Label htmlFor="ncr-concession">Concession reference</Label>
                                <Input id="ncr-concession" value={reference} onChange={(e) => setReference(e.target.value)}
                                       placeholder="Customer or design approval: PO#, email reference, document number" />
                                <p className="text-xs text-muted-foreground">
                                    {type === "REPAIR" ? "Repair" : "Use As Is"} accepts nonconforming product and needs one.
                                </p>
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="ncr-notes">Notes</Label>
                            <Textarea id="ncr-notes" value={notes} onChange={(e) => setNotes(e.target.value)}
                                      className="resize-none" placeholder="Why — kept on each part's disposition" />
                        </div>
                        {type === "SCRAP" && (
                            <p className="text-sm text-destructive">
                                The parts are scrapped as soon as this is recorded. While a disposition is open its
                                decision can be changed, with a reason, which un-scraps the part.
                            </p>
                        )}
                        {error && <p className="text-sm text-destructive">{error}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                        <Button disabled={!type || decide.isPending} onClick={submit}
                                variant={type === "SCRAP" ? "destructive" : "default"}>
                            {decide.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {canApprove ? "Record decision" : "Co-sign and record"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
            <SecondPersonCosignDialog
                open={cosignOpen}
                onOpenChange={(v) => { setCosignOpen(v); if (!v) setCosignError(null); }}
                title="Authorize disposition decision"
                description={`Recording "${decisionLabel(type) ?? type}" for ${count} part${count === 1 ? "" : "s"} needs approval authority. An authorized colleague can co-sign here; the decision is recorded under their name.`}
                emailLabel="Approver email"
                confirmationText="I authorize this disposition decision."
                confirmLabel="Authorize"
                error={cosignError}
                pending={decide.isPending}
                onConfirm={(creds) => decide.mutate(creds)}
            />
        </>
    );
}

function AddPartsDialog({ ncr, open, onOpenChange, onDone }: {
    ncr: Ncr; open: boolean; onOpenChange: (o: boolean) => void; onDone: () => void;
}) {
    const [parts, setParts] = useState<string[]>([]);
    const [reason, setReason] = useState("");
    const [search, setSearch] = useState("");
    const { data } = useRetrieveParts({ limit: 100, search });
    const on = new Set(ncr.members.map((m) => String(m.part_id)));

    useEffect(() => { if (open) { setParts([]); setReason(""); } }, [open]);

    const add = useMutation({
        mutationFn: () => api.api_NCRs_add_parts_create({ parts, ...(reason.trim() ? { reason: reason.trim() } : {}) },
            { params: { id: String(ncr.id) } }),
        meta: { errorMessage: "Couldn't add the parts", successMessage: "Parts added" },
        onSuccess: () => { onOpenChange(false); onDone(); },
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add parts to {ncr.ncr_number}</DialogTitle>
                    <DialogDescription>
                        Each part is held, gets a failed inspection record, and waits for its own decision under
                        this NCR.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <MultiPicker
                        label="Parts"
                        items={(data?.results ?? []).filter((p) => !on.has(String(p.id))).map((p) => ({
                            id: p.id, label: p.ERP_id,
                            ...(p.part_type_name ? { description: p.part_type_name } : {}),
                        }))}
                        selected={parts}
                        onChange={setParts}
                        onSearch={setSearch}
                        placeholder="Choose the parts"
                        searchPlaceholder="Search parts..."
                        emptyHint="No parts found."
                    />
                    <div className="space-y-2">
                        <Label htmlFor="ncr-add-reason">Why these parts</Label>
                        <Textarea id="ncr-add-reason" value={reason} onChange={(e) => setReason(e.target.value)}
                                  className="resize-none" placeholder="e.g. Same grinder setup" />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button disabled={!parts.length || add.isPending} onClick={() => add.mutate()}>
                        {add.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Add {parts.length || ""} part{parts.length === 1 ? "" : "s"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ---- What is wrong -----------------------------------------------------------------

function HeaderCard({ ncr, canEdit, onChanged }: { ncr: Ncr; canEdit: boolean; onChanged: () => void }) {
    const [description, setDescription] = useState(ncr.description ?? "");
    const [severity, setSeverity] = useState<string>(ncr.severity ?? "MAJOR");
    useEffect(() => { setDescription(ncr.description ?? ""); setSeverity(ncr.severity ?? "MAJOR"); },
        [ncr.description, ncr.severity]);
    const dirty = description !== (ncr.description ?? "") || severity !== (ncr.severity ?? "MAJOR");
    // Once anything is decided, severity may only rise (the server refuses a lowering).
    const decided = ncr.members.some((m) => !!m.disposition_type);
    const rank = ["MINOR", "MAJOR", "CRITICAL"];

    const save = useMutation({
        mutationFn: () => api.api_NCRs_partial_update(
            { description, severity: severity as "CRITICAL" | "MAJOR" | "MINOR" },
            { params: { id: String(ncr.id) } }),
        meta: { errorMessage: "Couldn't save the NCR", successMessage: "NCR saved" },
        onSuccess: onChanged,
    });

    return (
        <Card>
            <CardHeader><CardTitle>What's wrong</CardTitle></CardHeader>
            <CardContent className="space-y-4">
                {canEdit ? (
                    <>
                        <Textarea value={description} onChange={(e) => setDescription(e.target.value)}
                                  className="resize-none" rows={4} aria-label="Description" />
                        <div className="flex flex-wrap items-end gap-3">
                            <div className="space-y-2">
                                <Label>Severity</Label>
                                <Select value={severity} onValueChange={(v) => v && setSeverity(v)}>
                                    <SelectTrigger className="w-[300px]"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {/* Only the severities it may still take are listed. */}
                                        {SEVERITIES.filter((s) => !decided || rank.indexOf(s.value) >= rank.indexOf(ncr.severity ?? "MINOR"))
                                            .map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button className="ml-auto" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
                                {save.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Save
                            </Button>
                        </div>
                        {decided && (
                            <p className="text-xs text-muted-foreground">
                                Decided at this severity: it can be raised, not lowered.
                            </p>
                        )}
                    </>
                ) : (
                    <p className="whitespace-pre-wrap text-sm">
                        {ncr.description || <span className="text-muted-foreground">No description recorded.</span>}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}

function ContainmentCard({ ncr, canEdit, onChanged }: { ncr: Ncr; canEdit: boolean; onChanged: () => void }) {
    const [action, setAction] = useState(ncr.containment_action ?? "");
    useEffect(() => setAction(ncr.containment_action ?? ""), [ncr.containment_action]);
    // Who physically did it, when that wasn't the person recording it (user decision
    // 2026-10-07: the record says who vouched for it as well as who did it).
    const [performedBy, setPerformedBy] = useState<number | null>(ncr.containment_performed_by ?? null);
    const done = !!ncr.containment_completed_at;
    const { data: employees } = useQuery({
        queryKey: ["employee-options", 0],
        queryFn: () => api.api_Employees_Options_list({ queries: { offset: 0 } }),
        enabled: canEdit && !done,
    });

    const record = useMutation({
        mutationFn: async () => {
            if (action !== (ncr.containment_action ?? "") || performedBy !== (ncr.containment_performed_by ?? null)) {
                await api.api_NCRs_partial_update({ containment_action: action, containment_performed_by: performedBy },
                    { params: { id: String(ncr.id) } });
            }
            return api.api_NCRs_containment_complete_create(undefined, { params: { id: String(ncr.id) } });
        },
        meta: { errorMessage: "Couldn't record the containment", successMessage: "Containment recorded" },
        onSuccess: onChanged,
    });

    return (
        <Card>
            <CardHeader>
                <CardTitle>Containment</CardTitle>
                <CardDescription>
                    The immediate action taken to prevent escape — once, for everything this NCR covers.
                    {(ncr.severity === "CRITICAL" || ncr.severity === "MAJOR") && !done
                        && " A decision under a Critical or Major NCR can't be closed until it's recorded."}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                {canEdit && !done ? (
                    <>
                        <Textarea value={action} onChange={(e) => setAction(e.target.value)} className="resize-none"
                                  aria-label="Containment action"
                                  placeholder="e.g. Segregated the run; re-checked the other bores from this setup" />
                        <div className="space-y-2">
                            <Label>Performed by <span className="text-muted-foreground">(if not you)</span></Label>
                            <Combobox
                                value={performedBy == null ? null : String(performedBy)}
                                onChange={(v) => setPerformedBy(v ? Number(v) : null)}
                                options={(employees?.results ?? []).map((e) => ({
                                    value: String(e.id),
                                    label: e.full_name?.trim() || e.email || e.username || "Unknown",
                                }))}
                                placeholder="Select employee"
                                searchPlaceholder="Search..."
                                emptyText="No employees found."
                                clearLabel="Nobody else"
                            />
                        </div>
                        <div className="flex justify-end">
                            <Button disabled={!action.trim() || record.isPending} onClick={() => record.mutate()}>
                                {record.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Record containment
                            </Button>
                        </div>
                    </>
                ) : (
                    <>
                        <p className="whitespace-pre-wrap text-sm">
                            {ncr.containment_action || <span className="text-muted-foreground">No containment action recorded.</span>}
                        </p>
                        {done && (
                            <p className="text-xs text-muted-foreground">
                                Recorded by {ncr.containment_completed_by_name ?? "—"} on{" "}
                                {new Date(ncr.containment_completed_at!).toLocaleString()}
                            </p>
                        )}
                    </>
                )}
                {/* Evidence of the containment: photos, segregation tags. */}
                {canEdit && (
                    <div className="border-t pt-3">
                        <DocumentUploader objectId={String(ncr.id)} contentType="ncr" documentTypeCode="CONT_EVD"
                                          title="Attach Containment Evidence" compact />
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ---- Context ---------------------------------------------------------------------

function FoundCard({ ncr }: { ncr: Ncr }) {
    const row = (label: string, value: React.ReactNode) => (
        <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">{label}</span>
            <span className="text-right">{value ?? "—"}</span>
        </div>
    );
    return (
        <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Where it was found</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
                {row("Work order", ncr.work_order
                    ? <Link to="/workorder/$workOrderId" params={{ workOrderId: String(ncr.work_order) }}
                            className="text-primary underline-offset-2 hover:underline">{ncr.work_order_erp_id}</Link>
                    : null)}
                {row("Step", ncr.step_name)}
                {ncr.batch_execution && row("Failed batch load", `${ncr.members.length} parts`)}
                {row("Raised by", ncr.raised_by_name)}
                {row("Opened", new Date(ncr.created_at).toLocaleString())}
                {ncr.closed_at && row("Closed", new Date(ncr.closed_at).toLocaleString())}
                {/* Combined NCRs, both ways (services/qms/ncr.combine_ncrs). */}
                {ncr.combined_into && row("Combined into",
                    <Link to="/quality/ncrs/$ncrId" params={{ ncrId: String(ncr.combined_into) }}
                          className="font-mono text-primary underline-offset-2 hover:underline">
                        {ncr.combined_into_number}
                    </Link>)}
                {ncr.combined_from.length > 0 && row("Combined from",
                    <span className="flex flex-wrap justify-end gap-x-2">
                        {ncr.combined_from.map((n) => (
                            <Link key={String(n.id)} to="/quality/ncrs/$ncrId" params={{ ncrId: String(n.id) }}
                                  className="font-mono text-primary underline-offset-2 hover:underline">
                                {n.ncr_number}
                            </Link>
                        ))}
                    </span>)}
            </CardContent>
        </Card>
    );
}

function CapaCard({ ncr, onChanged }: { ncr: Ncr; onChanged: () => void }) {
    const canDecide = usePermissionSet().has("initiate_capa");
    const [asking, setAsking] = useState<"NOT_REQUIRED" | "DEFERRED" | null>(null);
    const record = useMutation({
        mutationFn: (v: { decision: "NOT_REQUIRED" | "DEFERRED"; note: string }) =>
            api.api_NCRs_capa_decision_create(v, { params: { id: String(ncr.id) } }),
        meta: { errorMessage: "Couldn't record the CAPA decision", successMessage: "CAPA decision recorded" },
        onSuccess: () => { setAsking(null); onChanged(); },
    });
    const decision = ncr.capa_decision;

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm">CAPA</CardTitle>
                <CardDescription>Whether this nonconformance needs corrective action — decided, not assumed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
                {decision ? (
                    <div className="space-y-1">
                        <Badge variant="outline">{CAPA_LABEL[decision] ?? decision}</Badge>
                        {ncr.capa_decision_note && <p className="whitespace-pre-wrap">{ncr.capa_decision_note}</p>}
                        {ncr.capa_decided_by_name && (
                            <p className="text-xs text-muted-foreground">
                                {ncr.capa_decided_by_name}
                                {ncr.capa_decided_at && `, ${new Date(ncr.capa_decided_at).toLocaleDateString()}`}
                            </p>
                        )}
                    </div>
                ) : (
                    <p className="text-amber-600 dark:text-amber-400">Not decided yet.</p>
                )}
                {canDecide && decision !== "PROMOTED" && (
                    <div className="flex flex-wrap gap-2">
                        <Button size="sm" asChild>
                            <Link to="/quality/capas/new"
                                  search={{ quality_reports: ncr.report_ids.map(String).join(",") || undefined }}>
                                Raise CAPA
                            </Link>
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setAsking("NOT_REQUIRED")}>No CAPA needed</Button>
                        <Button size="sm" variant="outline" onClick={() => setAsking("DEFERRED")}>Defer</Button>
                    </div>
                )}
                {ncr.capa_ids.length > 0 && (
                    <div className="space-y-1">
                        {ncr.capa_ids.map((id) => (
                            <Link key={String(id)} to="/quality/capas/$id" params={{ id: String(id) }}
                                  className="flex items-center gap-1.5 text-primary underline-offset-2 hover:underline">
                                <ExternalLink className="h-3.5 w-3.5" /> Linked CAPA
                            </Link>
                        ))}
                    </div>
                )}
            </CardContent>
            <ReasonPromptDialog
                open={asking !== null}
                onOpenChange={(o) => { if (!o) setAsking(null); }}
                title={asking === "DEFERRED" ? "Defer the CAPA decision" : "No CAPA needed"}
                description="The reason is what an auditor reads."
                placeholder={asking === "DEFERRED" ? "Why it can wait, and until when" : "e.g. One-off: the disposition handles it"}
                confirmLabel="Record"
                pending={record.isPending}
                onSubmit={(note) => asking && record.mutate({ decision: asking, note })}
            />
        </Card>
    );
}

/** The NCR's documents: what was filed under it (containment evidence from the
 *  Containment card included) and what was attached to it from a document's page. */
function DocumentsCard({ ncr }: { ncr: Ncr }) {
    const [open, setOpen] = useState(false);
    const canAttach = usePermissionSet().has("add_documents");
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm">Documents</CardTitle>
                <CardDescription>Evidence for this NCR: containment photos, segregation tags, concessions.</CardDescription>
            </CardHeader>
            <CardContent>
                <Button type="button" variant="outline" size="sm" className="w-full" onClick={() => setOpen(true)}>
                    <FileText className="mr-2 h-4 w-4" />
                    View or attach documents
                </Button>
                <EntityDocumentsEditor
                    contentTypeModel="ncr"
                    objectId={String(ncr.id)}
                    label={ncr.ncr_number}
                    description="Evidence for this NCR: containment photos, segregation tags, concessions."
                    open={open}
                    onOpenChange={setOpen}
                    readOnly={!canAttach}
                />
            </CardContent>
        </Card>
    );
}

function ReportsCard({ ncr }: { ncr: Ncr }) {
    if (!ncr.reports.length) return null;
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm">Inspection records ({ncr.reports.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
                {ncr.reports.map((r) => (
                    <Link key={String(r.id)} to="/details/$model/$id" params={{ model: "QualityReports", id: String(r.id) }}
                          className="flex items-center justify-between gap-2 rounded-md border p-2 text-sm hover:bg-muted/50">
                        <span className="flex items-center gap-1.5 font-mono text-primary">
                            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                            {r.report_number || "Inspection record"}
                        </span>
                        <span className="text-xs text-muted-foreground">{r.part_erp_id ?? ""}</span>
                        <Badge variant={r.status === "FAIL" ? "destructive" : "outline"}>{r.status}</Badge>
                    </Link>
                ))}
            </CardContent>
        </Card>
    );
}
