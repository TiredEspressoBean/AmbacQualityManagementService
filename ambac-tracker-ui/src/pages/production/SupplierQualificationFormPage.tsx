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
    useCreateSupplierQualification, useUpdateSupplierQualification,
    useRetrieveSupplierQualification,
} from "@/hooks/useSupplierQualifications";
import { EntityDocumentsEditor } from "@/components/documents/EntityDocumentsEditor";
import { FileText } from "lucide-react";

const SCOPE_TYPES = [
    { value: "PART_TYPE", label: "Part Type" },
    { value: "COMMODITY", label: "Commodity" },
    { value: "SPECIAL_PROCESS", label: "Special Process" },
];
const BASES = ["AUDIT", "PPAP", "FAI", "SURVEY", "HISTORICAL"];

export function SupplierQualificationFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false }) as { qualId?: string };
    const qualId = params.qualId;
    const isEdit = !!qualId;

    const { data: existing } = useRetrieveSupplierQualification(qualId);
    const { data: companies } = useRetrieveCompanies({ limit: 500 } as never);
    const { data: partTypes } = useRetrievePartTypes({ limit: 500 } as never);
    const create = useCreateSupplierQualification();
    const update = useUpdateSupplierQualification();

    const [supplier, setSupplier] = useState("");
    const [scopeType, setScopeType] = useState("PART_TYPE");
    const [partType, setPartType] = useState("");
    const [scopeLabel, setScopeLabel] = useState("");
    const [basis, setBasis] = useState("");
    const [effectiveDate, setEffectiveDate] = useState("");
    const [expiryDate, setExpiryDate] = useState("");
    const [notes, setNotes] = useState("");
    const [docsOpen, setDocsOpen] = useState(false);

    useEffect(() => {
        if (!existing) return;
        setSupplier(String(existing.supplier ?? ""));
        setScopeType(existing.scope_type ?? "PART_TYPE");
        setPartType(existing.part_type ? String(existing.part_type) : "");
        setScopeLabel(existing.scope_label ?? "");
        setBasis(existing.basis ?? "");
        setEffectiveDate(existing.effective_date ?? "");
        setExpiryDate(existing.expiry_date ?? "");
        setNotes(existing.notes ?? "");
    }, [existing]);

    const isPartTypeScope = scopeType === "PART_TYPE";

    const submit = async () => {
        if (!supplier) return toast.error("Supplier is required");
        if (isPartTypeScope && !partType) return toast.error("Part type is required for PART_TYPE scope");
        if (!isPartTypeScope && !scopeLabel) return toast.error("Scope label is required");

        const body: Record<string, unknown> = {
            supplier, scope_type: scopeType,
            part_type: isPartTypeScope ? partType : null,
            scope_label: isPartTypeScope ? "" : scopeLabel,
            basis: basis || "",
            effective_date: effectiveDate || null,
            expiry_date: expiryDate || null,
            notes,
        };
        try {
            if (isEdit) {
                await update.mutateAsync({ id: qualId as string, body });
                toast.success("Qualification updated");
            } else {
                await create.mutateAsync(body);
                toast.success("Qualification created (PENDING)");
            }
            navigate({ to: "/production/supplier-qualifications" });
        } catch {
            toast.error("Save failed");
        }
    };

    return (
        <div className="mx-auto max-w-2xl space-y-4 p-2">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold tracking-tight">
                    {isEdit ? "Edit qualification" : "New supplier qualification"}
                </h1>
                {isEdit && (
                    <Button variant="outline" size="sm" onClick={() => setDocsOpen(true)}>
                        <FileText className="h-4 w-4 mr-1" /> Documents (cert, audit, PPAP)
                    </Button>
                )}
            </div>
            {isEdit && qualId && (
                <EntityDocumentsEditor
                    contentTypeModel="supplierqualification"
                    objectId={qualId}
                    label="Qualification"
                    description="Audit reports, certificate of registration, PPAP/FAI package, supplier survey."
                    open={docsOpen}
                    onOpenChange={setDocsOpen}
                />
            )}
            <Card>
                <CardHeader><CardTitle className="text-base">Scope & basis</CardTitle></CardHeader>
                <CardContent className="space-y-4">
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

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>Scope type</Label>
                            <Select value={scopeType} onValueChange={setScopeType}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {SCOPE_TYPES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        {isPartTypeScope ? (
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
                        ) : (
                            <div className="space-y-1.5">
                                <Label>{scopeType === "COMMODITY" ? "Commodity" : "Special process"}</Label>
                                <Input value={scopeLabel} onChange={(e) => setScopeLabel(e.target.value)}
                                    placeholder={scopeType === "COMMODITY" ? "e.g. Castings" : "e.g. Heat Treat AMS2750"} />
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1.5">
                            <Label>Basis</Label>
                            <Select value={basis || "NONE"} onValueChange={(v) => setBasis(v === "NONE" ? "" : v)}>
                                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="NONE">—</SelectItem>
                                    {BASES.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
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
                        <Label>Notes</Label>
                        <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
                    </div>

                    {!isEdit && (
                        <p className="text-xs text-muted-foreground">
                            Created as PENDING. Grant it (or submit for approval) from the list once reviewed.
                        </p>
                    )}

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => navigate({ to: "/production/supplier-qualifications" })}>Cancel</Button>
                        <Button onClick={submit}>{isEdit ? "Save" : "Create"}</Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
