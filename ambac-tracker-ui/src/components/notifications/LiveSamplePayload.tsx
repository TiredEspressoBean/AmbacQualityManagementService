/**
 * Editable sample payload that drives the live "would fire?" preview.
 *
 * Each field renders as an inline editor matching its CelType:
 *   - enum string → chip group (one-tap to flip values)
 *   - number      → small number input
 *   - string      → text input
 *   - datetime    → read-only (preview doesn't support datetime conditions yet)
 *
 * The user can mutate the sample to ask "what if severity were major?"
 * without re-imagining the payload.
 */
import type { PayloadField } from "@/lib/notifications/payloadSchemas";
import { fieldLabel } from "@/lib/notifications/simpleConditions";
import { Input } from "@/components/ui/input";

interface Props {
    fields: PayloadField[];
    values: Record<string, unknown>;
    onChange: (next: Record<string, unknown>) => void;
}

export function LiveSamplePayload({ fields, values, onChange }: Props) {
    const setField = (name: string, value: unknown) =>
        onChange({ ...values, [name]: value });

    return (
        <div className="space-y-2">
            {fields.map((field) => (
                <div key={field.name} className="flex items-center justify-between gap-2">
                    <div className="text-xs text-muted-foreground min-w-0 flex-1">
                        {fieldLabel(field)}
                    </div>
                    <div className="text-xs">
                        <FieldEditor
                            field={field}
                            value={values[field.name]}
                            onChange={(v) => setField(field.name, v)}
                        />
                    </div>
                </div>
            ))}
        </div>
    );
}

function FieldEditor({
    field,
    value,
    onChange,
}: {
    field: PayloadField;
    value: unknown;
    onChange: (v: unknown) => void;
}) {
    if (field.enum && field.enum.length > 0) {
        const current = typeof value === "string" ? value : "";
        return (
            <div className="flex gap-1">
                {field.enum.map((opt) => {
                    const selected = current === opt;
                    return (
                        <button
                            key={opt}
                            type="button"
                            onClick={() => onChange(opt)}
                            className={
                                "rounded px-1.5 py-0.5 text-[11px] border transition-colors " +
                                (selected
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "bg-background hover:bg-muted")
                            }
                        >
                            {opt}
                        </button>
                    );
                })}
            </div>
        );
    }

    if (field.type === "number") {
        return (
            <Input
                type="number"
                value={typeof value === "number" ? value : ""}
                onChange={(e) =>
                    onChange(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="h-7 w-24 text-xs"
            />
        );
    }

    if (field.type === "datetime") {
        return (
            <span className="font-mono text-muted-foreground">
                {typeof value === "string" ? value : "—"}
            </span>
        );
    }

    return (
        <Input
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            className="h-7 w-44 text-xs"
        />
    );
}
