import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api } from "@/lib/api/generated";
import { useRetrieveParts } from "@/hooks/parts";
import { invalidateAfterNcrChange, partPickerDescription, useOpenNcrByPart } from "@/hooks/ncrs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { RequiredMark } from "@/components/ui/required-mark";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { MultiPicker } from "@/components/ui/multi-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { CreateNcrSearchParams } from "@/lib/routes/search-params";
import { SEVERITIES, type Severity } from "@/lib/quality-labels";
import { DefectRowsEditor, toDefectRowsPayload, worstSeverity, type DefectRow } from "@/components/quality/DefectRowsEditor";


/** Raise one NCR over parts a person picks: each part gets a failed inspection record
 *  and its own decision under the NCR, and is held until it's decided. */
export function NcrCreatePage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const search = useSearch({ strict: false }) as CreateNcrSearchParams;
    const preset = (search.parts ?? "").split(",").filter(Boolean);

    const [parts, setParts] = useState<string[]>(preset);
    const [description, setDescription] = useState("");
    const [severity, setSeverity] = useState<Severity>("MAJOR");
    // What was found — the same on every part's failed record. Severity follows the
    // worst defect until it's chosen by hand.
    const [defects, setDefects] = useState<DefectRow[]>([]);
    const [severityChosen, setSeverityChosen] = useState(false);
    const onDefects = (rows: DefectRow[]) => {
        setDefects(rows);
        const worst = worstSeverity(rows);
        if (!severityChosen && worst) setSeverity(worst);
    };
    const [partSearch, setPartSearch] = useState("");

    const { data: partsData } = useRetrieveParts({ limit: 100, search: partSearch });
    // Parts handed over from another page may not be in the first 100: label them anyway,
    // in one request.
    const { data: presetData } = useQuery({
        queryKey: ["parts", "list", { id__in: preset }],
        queryFn: () => api.api_Parts_list({ queries: { id__in: preset, limit: preset.length } }),
        enabled: preset.length > 0,
    });
    const labels = Object.fromEntries((presetData?.results ?? []).map((p) => [p.id, p.ERP_id]));
    const elsewhere = useOpenNcrByPart();
    const back = () => navigate({ to: search.from ?? "/quality/ncrs" });

    const raise = useMutation({
        mutationFn: () => api.api_NCRs_create({
            parts, description: description.trim(), severity,
            ...(defects.length ? { defect_rows: toDefectRowsPayload(defects) } : {}),
        }),
        onSuccess: (ncr) => {
            void invalidateAfterNcrChange(queryClient);  // its parts are held now
            navigate({ to: "/quality/ncrs/$ncrId", params: { ncrId: String(ncr.id) } });
        },
        meta: { errorMessage: "Couldn't raise the NCR", successMessage: "NCR raised" },
    });

    const ready = parts.length > 0 && description.trim().length > 0;
    // Raising one is add_ncr's; say so here rather than letting the save refuse.
    const { has, isLoading: permsLoading } = usePermissionSet();
    if (!permsLoading && !has("add_ncr")) {
        return (
            <div className="container max-w-3xl py-8 px-4 md:px-6">
                <p className="text-sm text-muted-foreground">
                    Raising an NCR needs the permission to flag a nonconformance. Ask a lead or QA.
                </p>
            </div>
        );
    }

    return (
        <div className="container max-w-3xl space-y-6 py-8 px-4 md:px-6">
            <Button variant="ghost" size="sm" onClick={back}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                {search.from ? "Back" : "NCRs"}
            </Button>
            <Card>
                <CardHeader>
                    <CardTitle>Raise NCR</CardTitle>
                    <CardDescription>
                        One nonconformance over the parts it covers. Each part gets a failed
                        inspection record saying what's wrong and waits for its own decision
                        under this NCR. Parts still here are held; shipped/completed ones are recorded.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                    <MultiPicker
                        label="Parts"
                        required
                        items={(partsData?.results ?? []).map((p) => ({
                            id: p.id, label: p.ERP_id,
                            description: partPickerDescription(p, elsewhere.get(String(p.id))),
                        }))}
                        selected={parts}
                        onChange={setParts}
                        onSearch={setPartSearch}
                        selectedLabels={labels}
                        placeholder="Choose the parts"
                        searchPlaceholder="Search parts..."
                        emptyHint="No parts found."
                    />
                    <div className="space-y-2">
                        <Label htmlFor="ncr-description">What's wrong<RequiredMark /></Label>
                        <Textarea id="ncr-description" value={description}
                                  onChange={(e) => setDescription(e.target.value)}
                                  placeholder="e.g. Bores oversize from grinder setup 2 — 4.007 against 4.005 max"
                                  className="resize-none" rows={4} />
                    </div>
                    <div className="space-y-2">
                        <Label>Defects found</Label>
                        <DefectRowsEditor rows={defects} onChange={onDefects}
                                          emptyText="None recorded yet. A defect here goes on each part's failed record, for defect analysis." />
                        {parts.length > 1 && defects.length > 0 && (
                            <p className="text-xs text-muted-foreground">
                                The same defects go on every part's record. A finding on one part alone can be added on the NCR afterwards.
                            </p>
                        )}
                    </div>
                    <div className="space-y-2">
                        <Label>Severity<RequiredMark /></Label>
                        <Select value={severity} onValueChange={(v) => { if (v) { setSeverity(v as Severity); setSeverityChosen(true); } }}>
                            <SelectTrigger className="w-[320px]"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {SEVERITIES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="flex justify-end gap-2 border-t pt-4">
                        <Button variant="outline" onClick={back}>Cancel</Button>
                        <Button disabled={!ready || raise.isPending} onClick={() => raise.mutate()}>
                            {raise.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Raise NCR{parts.length > 1 ? ` over ${parts.length} parts` : ""}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
