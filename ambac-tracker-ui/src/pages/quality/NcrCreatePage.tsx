import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api } from "@/lib/api/generated";
import { useRetrieveParts } from "@/hooks/parts";
import { invalidateAfterNcrChange } from "@/hooks/ncrs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { MultiPicker } from "@/components/ui/multi-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { CreateNcrSearchParams } from "@/lib/routes/search-params";

type Severity = "CRITICAL" | "MAJOR" | "MINOR";

const SEVERITIES: { value: Severity; label: string }[] = [
    { value: "CRITICAL", label: "Critical - Safety/Regulatory Impact" },
    { value: "MAJOR", label: "Major - Functional Impact" },
    { value: "MINOR", label: "Minor - Cosmetic Only" },
];

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
    const [partSearch, setPartSearch] = useState("");

    const { data: partsData } = useRetrieveParts({ limit: 100, search: partSearch });
    // Parts handed over from another page may not be in the first 100: label them anyway.
    const presetParts = useQueries({
        queries: preset.map((id) => ({
            queryKey: ["parts", "detail", id] as const,
            queryFn: () => api.api_Parts_retrieve({ params: { id } }),
        })),
        combine: (rs) => rs.map((r) => r.data).filter((p): p is NonNullable<typeof p> => !!p),
    });
    const labels = Object.fromEntries(presetParts.map((p) => [p.id, p.ERP_id]));

    const raise = useMutation({
        mutationFn: () => api.api_NCRs_create({ parts, description: description.trim(), severity }),
        onSuccess: (ncr) => {
            void invalidateAfterNcrChange(queryClient);  // its parts are held now
            navigate({ to: "/quality/ncrs/$ncrId", params: { ncrId: String(ncr.id) } });
        },
        meta: { errorMessage: "Couldn't raise the NCR", successMessage: "NCR raised" },
    });

    const ready = parts.length > 0 && description.trim().length > 0;

    return (
        <div className="container max-w-3xl space-y-6 py-8 px-4 md:px-6">
            <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/quality/ncrs" })}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                NCRs
            </Button>
            <Card>
                <CardHeader>
                    <CardTitle>Raise NCR</CardTitle>
                    <CardDescription>
                        One nonconformance over the parts it covers. Each part is held, gets a
                        failed inspection record saying what's wrong, and waits for its own
                        decision under this NCR.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                    <MultiPicker
                        label="Parts"
                        items={(partsData?.results ?? []).map((p) => ({
                            id: p.id, label: p.ERP_id,
                            ...(p.part_type_name ? { description: p.part_type_name } : {}),
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
                        <Label htmlFor="ncr-description">What's wrong</Label>
                        <Textarea id="ncr-description" value={description}
                                  onChange={(e) => setDescription(e.target.value)}
                                  placeholder="e.g. Bores oversize from grinder setup 2 — 4.007 against 4.005 max"
                                  className="resize-none" rows={4} />
                    </div>
                    <div className="space-y-2">
                        <Label>Severity</Label>
                        <Select value={severity} onValueChange={(v) => v && setSeverity(v as Severity)}>
                            <SelectTrigger className="w-[320px]"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {SEVERITIES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="flex justify-end gap-2 border-t pt-4">
                        <Button variant="outline" onClick={() => navigate({ to: "/quality/ncrs" })}>Cancel</Button>
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
