/**
 * Shared smart-token chip renderer.
 *
 * Used by both the V2 rule editor's form-builder and the casual subscribe
 * sheet. A token like "In the last {days} days" renders as a single row
 * with the parameter ({days}) replaced by an inline editable input.
 */
import { AlertTriangle, Calendar, Tag, User, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import {
    getSmartToken,
    type SmartTokenDef,
    type SmartTokenInstance,
} from "@/lib/notifications/simpleConditions";

interface Props {
    token: SmartTokenInstance;
    onUpdate: (params: Record<string, string | number>) => void;
    onRemove: () => void;
}

export function SmartTokenRow({ token, onUpdate, onRemove }: Props) {
    const def = getSmartToken(token.tokenId);
    if (!def) {
        return (
            <div className="rounded-md border bg-amber-500/10 px-3 py-2 text-xs">
                Unknown smart token: {token.tokenId}
            </div>
        );
    }
    const segments = def.label.split(/(\{[^}]+\})/g);

    return (
        <div className="flex items-center gap-2 rounded-md border bg-primary/5 border-primary/30 p-2">
            <SmartTokenIcon name={def.icon} className="h-4 w-4 text-primary shrink-0" />
            <div className="flex flex-wrap items-center gap-1.5 flex-1 text-sm">
                {segments.map((seg, i) => {
                    const paramMatch = seg.match(/^\{([^}]+)\}$/);
                    if (!paramMatch) {
                        return seg ? <span key={i}>{seg}</span> : null;
                    }
                    const paramKey = paramMatch[1];
                    const param = def.params.find((p) => p.key === paramKey);
                    if (!param) return <span key={i}>{seg}</span>;
                    return (
                        <SmartTokenParamEditor
                            key={i}
                            param={param}
                            value={token.params[paramKey]}
                            onChange={(v) =>
                                onUpdate({ ...token.params, [paramKey]: v })
                            }
                        />
                    );
                })}
            </div>
            <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={onRemove}
                aria-label="Remove condition"
            >
                <X className="h-4 w-4" />
            </Button>
        </div>
    );
}

export function SmartTokenIcon({
    name,
    className,
}: {
    name: SmartTokenDef["icon"];
    className?: string;
}) {
    switch (name) {
        case "user":
            return <User className={className} />;
        case "calendar":
            return <Calendar className={className} />;
        case "alert":
            return <AlertTriangle className={className} />;
        case "tag":
            return <Tag className={className} />;
    }
}

function SmartTokenParamEditor({
    param,
    value,
    onChange,
}: {
    param: {
        key: string;
        label: string;
        type: "number" | "enum";
        default: string | number;
        options?: readonly string[];
    };
    value: string | number | undefined;
    onChange: (v: string | number) => void;
}) {
    if (param.type === "number") {
        const v = typeof value === "number" ? value : Number(param.default);
        return (
            <Input
                type="number"
                value={v}
                onChange={(e) =>
                    onChange(e.target.value === "" ? 0 : Number(e.target.value))
                }
                className="h-7 w-16 text-sm font-medium text-center"
            />
        );
    }
    const v = typeof value === "string" ? value : String(param.default);
    return (
        <Select value={v} onValueChange={onChange}>
            <SelectTrigger className="h-7 w-auto text-sm font-medium gap-1">
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                {(param.options ?? []).map((opt) => (
                    <SelectItem key={opt} value={opt}>
                        {opt}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
