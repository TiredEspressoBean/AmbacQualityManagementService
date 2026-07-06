import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import {
    useCreatePartApproval, useUpdatePartApproval, useRetrievePartApproval,
} from "@/hooks/usePartApprovals";
import { EntityDocumentsEditor } from "@/components/documents/EntityDocumentsEditor";
import { FileText } from "lucide-react";

const APPROVAL_TYPES = [
    { value: "PPAP", label: "PPAP (Production Part Approval Process)" },
    { value: "FAI", label: "FAI (First Article Inspection)" },
];

export function PartApprovalFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false }) as { approvalId?: string };
    const approvalId = params.approvalId;
    const isEdit = !!approvalId;

    const { data: existing } = useRetrievePartApproval(approvalId);
    const { data: companies } = useRetrieveCompanies({ limit: 500 } as never);
    const { data: partTypes } = useRetrievePartTypes({ limit: 500 } as never);
    const create = useCreatePartApproval();
    const update = useUpdatePartApproval();

    const [supplier, setSupplier] = useState("");
    const [partType, setPartType] = useState("");
    const [approvalType, setApprovalType] = useState("PPAP");
    const [reference, setReference] = useState("");
    const [effectiveDate, setEffectiveDate] = useState("");
    const [expiryDate, setExpiryDate] = useState("");
    const [notes, setNotes] = useState("");
    const [docsOpen, setDocsOpen] = useState(false);

    useEffect(() => {
        if (!existing) return;
        setSupplier(String(existing.supplier ?? ""));
        setPartType(existing.part_type ? String(existing.part_type) : "");
        setApprovalType(existing.approval_type ?? "PPAP");
        setReference(existing.reference ?? "");
        setEffectiveDate(existing.effective_date ?? "");
        setExpiryDate(existing.expiry_date ?? "");
        setNotes(existing.notes ?? "");
    }, [existing]);

    const submit = async () => {
        if (!supplier) return toast.error("Supplier is required");
        if (!partType) return toast.error("Part type is required");

        const body: Record<string, unknown> = {
            supplier, part_type: partType, approval_type: approvalType,
            reference, effective_date: effectiveDate || null,
            expiry_date: expiryDate || null, notes,
        };
        try {
            if (isEdit) {
                await update.mutateAsync({ id: approvalId as string, body });
                toast.success("Part approval updated");
            } else {
                await create.mutateAsync(body);
                toast.success("Part approval created (PENDING)");
            }
            navigate({ to: "/production/part-approvals" });
        } catch {
            toast.error("Save failed");
        }
    };

    return (
        <div className="mx-auto max-w-2xl space-y-4 p-2">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold tracking-tight">
                    {isEdit ? "Edit part approval" : "New part approval"}
                </h1>
                {isEdit && (
                    <Button variant="outline" size="sm" onClick={() => setDocsOpen(true)}>
                        <FileText className="h-4 w-4 mr-1" /> Documents (PPAP / FAI package)
                    </Button>
                )}
            </div>
            {isEdit && approvalId && (
                <EntityDocumentsEditor
                    contentTypeModel="partapproval"
                    objectId={approvalId}
                    label="Part approval"
                    description="PPAP package, FAI report (AS9102), control plan, PSW, dimensional results."
                    open={docsOpen}
                    onOpenChange={setDocsOpen}
                />
            )}
            <Card>
                <CardHeader><CardTitle className="text-base">Part, supplier & basis</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>Part type</Label>
                            <Select value={partType} onValueChange={setPartType}>
                                <SelectTrigger><SelectValue placeholder="Select part type…" /></SelectTrigger>
                                <SelectContent>
                                    {(partTypes?.results ?? []).map((p: any) => (
                                        <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Supplier</Label>
                            <Select value={supplier} onValueChange={setSupplier}>
                                <SelectTrigger><SelectValue placeholder="Select supplier…" /></SelectTrigger>
                                <SelectContent>
                                    {(companies?.results ?? []).map((c: any) => (
                                        <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1.5">
                            <Label>Approval type</Label>
                            <Select value={approvalType} onValueChange={setApprovalType}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {APPROVAL_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.value}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Effective</Label>
                            <Input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Expiry</Label>
                            <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <Label>Reference (PPAP/PSW #, FAI report #)</Label>
                        <Input value={reference} onChange={(e) => setReference(e.target.value)}
                            placeholder="e.g. PSW-2026-014 / FAI-8842" />
                    </div>

                    <div className="space-y-1.5">
                        <Label>Notes</Label>
                        <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
                    </div>

                    {!isEdit && (
                        <p className="text-xs text-muted-foreground">
                            Created as PENDING. Grant it (or submit for approval) from the list once the package is reviewed.
                        </p>
                    )}

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => navigate({ to: "/production/part-approvals" })}>Cancel</Button>
                        <Button onClick={submit}>{isEdit ? "Save" : "Create"}</Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
