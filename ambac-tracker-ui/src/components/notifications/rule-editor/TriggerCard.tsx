import {useState} from "react";
import {Check, Code, LayoutGrid, Sparkles} from "lucide-react";

import {Button} from "@/components/ui/button";
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";
import {Label} from "@/components/ui/label";
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue,} from "@/components/ui/select";
import {Textarea} from "@/components/ui/textarea";

import {SimpleConditionBuilder} from "@/components/notifications/SimpleConditionBuilder";
import {useNotificationEventCatalog} from "@/lib/notifications/eventCatalog";
import {CEL_SNIPPETS} from "@/lib/notifications/celSnippets";
import type {PayloadField} from "@/lib/notifications/payloadSchemas";
import type {ConditionGroup} from "@/lib/notifications/simpleConditions";
import type {RuleDraft} from "@/lib/notifications/ruleDraft";

export type EditorMode = "simple" | "advanced";

export function TriggerCard({
                                draft, patch, fields, mode, root, setRoot, onSwitchToSimple, onSwitchToAdvanced,
                            }: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
    fields: PayloadField[];
    mode: EditorMode;
    root: ConditionGroup;
    setRoot: (r: ConditionGroup) => void;
    onSwitchToSimple: () => void;
    onSwitchToAdvanced: () => void;
}) {
    const {events} = useNotificationEventCatalog();
    const event = events.find((e) => e.code === draft.eventCode);

    const insertField = (fieldName: string) => {
        const insertion = `payload.${fieldName}`;
        patch({
            conditionsSource: draft.conditionsSource ? `${draft.conditionsSource} ${insertion}` : insertion,
        });
    };
    const insertSnippet = (snippet: string) => {
        patch({
            conditionsSource: draft.conditionsSource ? `${draft.conditionsSource}\n${snippet}` : snippet,
        });
    };

    return (<Card>
            <CardHeader>
                <CardTitle className="text-base">Trigger</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="space-y-2">
                    <Label>Event</Label>
                    <Select
                        value={draft.eventCode}
                        onValueChange={(v) => patch({eventCode: v})}
                    >
                        <SelectTrigger>
                            <SelectValue/>
                        </SelectTrigger>
                        <SelectContent>
                            {events.map((e) => (<SelectItem key={e.code} value={e.code}>
                                    {e.label}
                                </SelectItem>))}
                        </SelectContent>
                    </Select>
                    {event && (<p className="text-xs text-muted-foreground">{event.description}</p>)}
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <Label>Condition</Label>
                        <ModeToggle
                            mode={mode}
                            onSimple={onSwitchToSimple}
                            onAdvanced={onSwitchToAdvanced}
                        />
                    </div>

                    {mode === "simple" ? (<SimpleConditionBuilder
                            fields={fields}
                            root={root}
                            onChange={setRoot}
                        />) : (<>
                            <Textarea
                                rows={5}
                                className="font-mono text-sm"
                                placeholder="payload.severity == 'critical'"
                                value={draft.conditionsSource}
                                onChange={(e) => patch({conditionsSource: e.target.value})}
                                aria-label="CEL condition expression"
                            />
                            <div className="flex flex-wrap items-center gap-2">
                                <InsertFieldPopover fields={fields} onPick={insertField}/>
                                <InsertSnippetPopover onInsert={insertSnippet}/>
                                <div className="flex-1"/>
                                <CelValidationBanner
                                    source={draft.conditionsSource}
                                    fields={fields}
                                />
                            </div>
                        </>)}
                </div>
            </CardContent>
        </Card>);
}

function ModeToggle({
                        mode, onSimple, onAdvanced,
                    }: {
    mode: EditorMode; onSimple: () => void; onAdvanced: () => void;
}) {
    return (<div className="inline-flex rounded-md border p-0.5">
            <Button
                type="button"
                size="sm"
                variant={mode === "simple" ? "default" : "ghost"}
                className="h-7 px-3 text-xs"
                onClick={onSimple}
            >
                <LayoutGrid className="h-3.5 w-3.5 mr-1.5"/>
                Simple
            </Button>
            <Button
                type="button"
                size="sm"
                variant={mode === "advanced" ? "default" : "ghost"}
                className="h-7 px-3 text-xs"
                onClick={onAdvanced}
            >
                <Code className="h-3.5 w-3.5 mr-1.5"/>
                Advanced (CEL)
            </Button>
        </div>);
}

function InsertFieldPopover({
                                fields, onPick,
                            }: {
    fields: PayloadField[]; onPick: (field: string) => void;
}) {
    const [open, setOpen] = useState(false);
    return (<Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button variant="outline" size="sm">
                    <Sparkles className="h-3.5 w-3.5 mr-1.5"/>
                    Insert field
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-72 p-0" align="start">
                <ul className="max-h-72 overflow-y-auto p-1">
                    {fields.length === 0 ? (<li className="px-3 py-2 text-xs text-muted-foreground">
                            No schema registered for this event.
                        </li>) : (fields.map((f) => (<li key={f.name}>
                                <button
                                    className="w-full text-left rounded px-2 py-1.5 hover:bg-muted text-xs"
                                    onClick={() => {
                                        onPick(f.name);
                                        setOpen(false);
                                    }}
                                    title={f.description}
                                >
                                    <code className="font-mono">{f.name}</code>
                                    <span className="text-muted-foreground ml-1">: {f.type}</span>
                                </button>
                            </li>)))}
                </ul>
            </PopoverContent>
        </Popover>);
}

function InsertSnippetPopover({onInsert}: { onInsert: (s: string) => void }) {
    const [open, setOpen] = useState(false);
    return (<Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button variant="outline" size="sm">
                    <Code className="h-3.5 w-3.5 mr-1.5"/>
                    Insert pattern
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-0" align="start">
                <ul className="max-h-72 overflow-y-auto p-1">
                    {CEL_SNIPPETS.map((s) => (<li key={s.label}>
                            <button
                                className="w-full text-left rounded px-2 py-1.5 hover:bg-muted text-xs"
                                onClick={() => {
                                    onInsert(s.expression);
                                    setOpen(false);
                                }}
                            >
                                <div className="font-medium">{s.label}</div>
                                <code className="text-muted-foreground font-mono break-all">
                                    {s.expression}
                                </code>
                            </button>
                        </li>))}
                </ul>
            </PopoverContent>
        </Popover>);
}

function CelValidationBanner({
                                 source, fields,
                             }: {
    source: string; fields: PayloadField[];
}) {
    if (!source.trim()) return null;
    const fieldNames = new Set(fields.map((f) => f.name));
    const referenced = Array.from(source.matchAll(/payload\.([a-zA-Z_][a-zA-Z0-9_]*)/g),).map((m) => m[1]);
    const unknown = referenced.filter((name) => !fieldNames.has(name));

    if (unknown.length === 0) {
        return (<div className="flex items-center gap-2 text-xs text-emerald-700 dark:text-emerald-400">
                <Check className="h-3.5 w-3.5"/>
                Looks valid. Backend will type-check on save.
            </div>);
    }
    return (<div
            className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-900 dark:text-amber-200 space-y-1">
            <div className="font-medium">Unknown field(s) on this event's payload</div>
            <ul className="ml-4 list-disc">
                {unknown.map((name) => {
                    const suggestion = closestField(name, fields);
                    return (<li key={name}>
                            <code className="font-mono">payload.{name}</code>
                            {suggestion && (<>
                                    {" — did you mean "}
                                    <code className="font-mono">payload.{suggestion}</code>?
                                </>)}
                        </li>);
                })}
            </ul>
        </div>);
}

function closestField(name: string, fields: PayloadField[]): string | null {
    const lc = name.toLowerCase();
    let best: { field: string; score: number } | null = null;
    for (const f of fields) {
        const score = sharedPrefix(lc, f.name.toLowerCase());
        if (!best || score > best.score) best = {field: f.name, score};
    }
    return best && best.score >= 2 ? best.field : null;
}

function sharedPrefix(a: string, b: string): number {
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    return i;
}