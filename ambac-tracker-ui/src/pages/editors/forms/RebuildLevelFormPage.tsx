import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import {
    useCreateRebuildScopePreset, useRetrieveRebuildScopePreset, useUpdateRebuildScopePreset,
} from "@/hooks/useRebuildScopePresets";
import { useRetrieveRepairCodes } from "@/hooks/useRepairCodes";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";

export function RebuildLevelFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useRetrieveRebuildScopePreset(id ?? "", { enabled: !!id });
    const { data: partTypesData } = useRetrievePartTypes({ limit: 200 });
    const { data: codesData } = useRetrieveRepairCodes({ limit: 200 });

    const [name, setName] = useState("");
    const [coreType, setCoreType] = useState("");
    const [isDefault, setIsDefault] = useState(false);
    const [codeIds, setCodeIds] = useState<Set<string>>(new Set());
    const [notes, setNotes] = useState("");

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setName(existing.name ?? "");
        setCoreType(existing.core_type ? String(existing.core_type) : "");
        setIsDefault(!!existing.is_default);
        setCodeIds(new Set((existing.codes ?? []).map(String)));
        setNotes(existing.notes ?? "");
    }, [mode, existing]);

    const partTypes = useMemo(() => partTypesData?.results ?? [], [partTypesData]);
    const codes = useMemo(() => codesData?.results ?? [], [codesData]);

    // A level is a pre-composed selection of codes, so the ones a FINDING raises are
    // not what you pick here — those arrive on their own. Showing them would invite
    // an engineer to add work that is already covered.
    const selectable = useMemo(
        () => codes.filter((c) => c.trigger === "PRESET" || c.trigger === "ALWAYS"),
        [codes],
    );

    const create = useCreateRebuildScopePreset();
    const update = useUpdateRebuildScopePreset();
    const saving = create.isPending || update.isPending;

    function toggleCode(codeId: string) {
        setCodeIds((prev) => {
            const next = new Set(prev);
            if (next.has(codeId)) next.delete(codeId);
            else next.add(codeId);
            return next;
        });
    }

    function submit() {
        if (!name.trim() || !coreType) {
            toast.error("A name and a core type are required");
            return;
        }
        const payload = {
            name: name.trim(),
            core_type: coreType,
            is_default: isDefault,
            codes: Array.from(codeIds),
            notes,
        };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Rebuild level updated" : "Rebuild level created");
            navigate({ to: "/editor/rebuild-levels" });
        };
        const onError = (err: unknown) => {
            // The serializer names the level already holding the default, so surface
            // THAT rather than "Request failed with status code 400" — the status tells
            // an engineer nothing about what they did or how to undo it.
            const body = apiErrorBody(err);
            const message =
                apiErrorField(body, "is_default") ??
                apiErrorField(body, "detail") ??
                apiErrorField(body, "non_field_errors") ??
                (err as Error)?.message ??
                "unknown error";
            toast.error(message);
        };

        if (mode === "edit" && id) {
            update.mutate({ id, data: payload }, { onSuccess, onError });
        } else {
            create.mutate(payload, { onSuccess, onError });
        }
    }

    if (mode === "edit" && isLoading) {
        return (
            <div className="max-w-3xl mx-auto py-10">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 w-64 rounded bg-muted" />
                    <div className="h-64 rounded bg-muted" />
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto py-10 space-y-6">
            <div className="flex items-center gap-3">
                <Button
                    variant="ghost" size="icon"
                    onClick={() => navigate({ to: "/editor/rebuild-levels" })}
                >
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">
                        {mode === "edit" ? "Edit rebuild level" : "New rebuild level"}
                    </h1>
                    <p className="text-muted-foreground">
                        What the shop sells before anything is found. Findings extend it.
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Identity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="level-name">Name</Label>
                        <Input
                            id="level-name" value={name} onChange={(e) => setName(e.target.value)}
                            placeholder="Standard rebuild"
                        />
                        <p className="text-xs text-muted-foreground">
                            What a customer would see on a quote.
                        </p>
                    </div>
                    <div className="space-y-1.5">
                        <Label>Core type</Label>
                        <Select value={coreType} onValueChange={(v) => v && setCoreType(v)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Pick the core type this level applies to" />
                            </SelectTrigger>
                            <SelectContent>
                                {partTypes.map((pt) => (
                                    <SelectItem key={pt.id} value={String(pt.id)}>
                                        {pt.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <label className="flex cursor-pointer items-start gap-2">
                        <Checkbox
                            checked={isDefault}
                            onCheckedChange={(v) => setIsDefault(v === true)}
                        />
                        <span className="text-sm">
                            Propose this automatically
                            <span className="block text-xs text-muted-foreground">
                                At most one level per core type can be the default. Setting a
                                second one is refused by the database rather than quietly
                                replacing the first.
                            </span>
                        </span>
                    </label>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">
                        Codes it includes{" "}
                        <span className="text-sm font-normal text-muted-foreground tabular-nums">
                            {codeIds.size} selected
                        </span>
                    </CardTitle>
                    <CardDescription>
                        Only codes that no finding raises on its own are listed. A
                        finding-raised code arrives when the finding does, so including it
                        here would add work that is already covered.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="max-h-72 space-y-2 overflow-y-auto rounded-md border p-3">
                        {selectable.length === 0 ? (
                            <p className="py-4 text-center text-sm text-muted-foreground">
                                No codes available. Author a repair code with "Always" or "Only
                                when a rebuild level includes it" first.
                            </p>
                        ) : (
                            selectable.map((c) => {
                                const cid = String(c.id);
                                return (
                                    <label
                                        key={cid}
                                        className="flex cursor-pointer items-start gap-2 text-sm"
                                    >
                                        <Checkbox
                                            checked={codeIds.has(cid)}
                                            onCheckedChange={() => toggleCode(cid)}
                                        />
                                        <span>
                                            <span className="font-mono">{c.code}</span> — {c.name}
                                            {c.trigger === "ALWAYS" && (
                                                <span className="block text-xs text-muted-foreground">
                                                    Always applies, with or without this level.
                                                </span>
                                            )}
                                        </span>
                                    </label>
                                );
                            })
                        )}
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Notes</CardTitle>
                </CardHeader>
                <CardContent>
                    <Textarea
                        value={notes} onChange={(e) => setNotes(e.target.value)}
                        placeholder="What this level covers, and what it deliberately does not"
                        rows={3}
                    />
                </CardContent>
            </Card>

            <div className="flex gap-3">
                <Button onClick={submit} disabled={saving} className="flex-1">
                    {saving ? "Saving…" : mode === "edit" ? "Save changes" : "Create rebuild level"}
                </Button>
                <Button
                    variant="ghost"
                    onClick={() => navigate({ to: "/editor/rebuild-levels" })}
                    disabled={saving}
                >
                    Cancel
                </Button>
            </div>
        </div>
    );
}
