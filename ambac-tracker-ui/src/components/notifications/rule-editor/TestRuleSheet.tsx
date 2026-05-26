import { useEffect, useMemo, useState } from "react";
import { Eye, FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

import { LiveSamplePayload } from "@/components/notifications/LiveSamplePayload";
import { getPayloadFields, getSamplePayload } from "@/lib/notifications/payloadSchemas";
import type { RuleDraft } from "@/lib/notifications/ruleDraft";

export function TestRuleSheet({
    open,
    onOpenChange,
    draft,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    draft: RuleDraft;
}) {
    const fields = useMemo(() => getPayloadFields(draft.eventCode), [draft.eventCode]);
    const baseline = useMemo(() => getSamplePayload(draft.eventCode), [draft.eventCode]);
    const [sample, setSample] = useState<Record<string, unknown>>(baseline);

    useEffect(() => {
        setSample(baseline);
    }, [baseline]);

    const result = useMemo(
        () => evaluateCelStub(draft.conditionsSource, sample, draft.ownerUserId),
        [draft.conditionsSource, sample, draft.ownerUserId],
    );

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <FlaskConical className="h-5 w-5 text-primary" />
                        Test rule
                    </SheetTitle>
                    <SheetDescription>
                        Adjust the sample payload to see whether your rule would fire. This
                        runs in the browser; the backend will re-evaluate on save with the
                        full CEL grammar.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-4 px-4">
                    <div className="rounded-md border bg-muted/30 px-3 py-2">
                        <div className="text-xs text-muted-foreground mb-2">
                            Sample payload — tap values to test variations.
                        </div>
                        <LiveSamplePayload
                            fields={fields}
                            values={sample}
                            onChange={setSample}
                        />
                    </div>

                    <div className="flex items-center justify-between rounded-md border px-3 py-3">
                        <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Would fire?</span>
                        </div>
                        <Badge
                            variant={result.fires && !result.error ? "default" : "secondary"}
                            className={cn(
                                "text-sm px-3 py-1",
                                result.error && "bg-amber-500/20 text-amber-900",
                            )}
                        >
                            {result.error ? "stub error" : result.fires ? "yes" : "no"}
                        </Badge>
                    </div>

                    {result.error && (
                        <p className="text-xs text-muted-foreground">
                            Demo evaluator can't parse this expression. Backend CEL will
                            handle the full grammar.
                        </p>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}

/**
 * Stub CEL evaluator. Handles equality on `payload.<field>` against a string
 * or number literal, `owner_user.id`, and `in [...]`. Anything else returns
 * `{ error: true }`. Backend CEL handles the full grammar on save.
 */
function evaluateCelStub(
    source: string,
    payload: Record<string, unknown>,
    ownerUserId: number | null,
): { fires: boolean; error: boolean } {
    const trimmed = source.trim();
    if (!trimmed) return { fires: true, error: false };

    try {
        let resolved = trimmed.replace(/payload\.([a-zA-Z_][a-zA-Z0-9_]*)/g, (_m, key) => {
            const value = payload[key];
            if (typeof value === "string") return JSON.stringify(value);
            if (typeof value === "number" || typeof value === "boolean") return String(value);
            return "undefined";
        });
        resolved = resolved.replace(/owner_user\.id/g, String(ownerUserId ?? "null"));
        resolved = resolved.replace(/\s+in\s+\[/g, ".includes(");
        resolved = resolved.replace(/\]/g, ")");
        resolved = resolved.replace(/(\w+)\.includes\(([^)]+)\)/g, "[$2].includes($1)");
        resolved = resolved.replace(/==/g, "===").replace(/!=/g, "!==");

        const fires = Boolean(Function(`"use strict"; return (${resolved});`)());
        return { fires, error: false };
    } catch {
        return { fires: false, error: true };
    }
}
