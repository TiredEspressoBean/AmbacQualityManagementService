/**
 * PersonnelRolesField — captures non-signature personnel on an inspection
 * event (operator, witness, trainer, trainee). Maps to
 * `QualityReportPersonnel` rows with the matching role.
 *
 * Signature roles (DETECTED_BY / VERIFIED_BY) live in the separate
 * `InspectionSignatures` node because their UX is "I attest now" rather
 * than "these people were involved."
 *
 * Engineer authoring: label, required, allowed roles (excludes signature
 * roles by default), min_rows.
 * Operator capture: array of `{ user_id, role, notes? }`.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Users, Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";

type NonSigRole = "OPERATOR" | "WITNESS" | "TRAINER" | "TRAINEE" | "INSPECTOR";

const ROLE_LABELS: Record<NonSigRole, string> = {
    OPERATOR: "Operator",
    WITNESS: "Witness",
    TRAINER: "Trainer",
    TRAINEE: "Trainee",
    INSPECTOR: "Inspector",
};
const ROLES: NonSigRole[] = ["OPERATOR", "INSPECTOR", "WITNESS", "TRAINER", "TRAINEE"];

type Attrs = {
    node_id: string;
    label: string;
    required: boolean;
    min_rows: number;
    default_role: NonSigRole;
};

type ResponseRow = { user_id: number; role: NonSigRole; notes?: string };

type UserShape = { id: number; username: string; first_name?: string; last_name?: string };

function displayName(u: UserShape): string {
    const full = `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim();
    return full || u.username;
}

export function PersonnelRolesFieldEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Default role for new rows</Label>
                <Select
                    value={a.default_role}
                    onValueChange={(v) => updateAttributes({ default_role: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {ROLES.map((r) => (
                            <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-2">
                <Label className="text-xs">Min rows</Label>
                <Input
                    type="number"
                    min={0}
                    value={String(a.min_rows ?? 1)}
                    onChange={(e) => updateAttributes({ min_rows: Number(e.target.value) || 0 })}
                    className="col-span-2 h-8 text-sm"
                />
            </div>
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required</Label>
                <Switch
                    checked={a.required}
                    onCheckedChange={(v) => updateAttributes({ required: v })}
                />
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const rows: ResponseRow[] = Array.isArray(value) ? (value as ResponseRow[]) : [];

    const { data: usersResp } = useRetrieveUsers();
    const users = (usersResp?.results ?? []) as UserShape[];

    const update = (next: ResponseRow[]) => {
        if (!isOperator) return;
        setValue(next);
    };
    const addRow = () => {
        const first = users[0];
        if (!first) return;
        update([...rows, { user_id: first.id, role: (a.default_role || "OPERATOR") as NonSigRole }]);
    };
    const setRow = (i: number, patch: Partial<ResponseRow>) => {
        const next = rows.slice();
        next[i] = { ...next[i], ...patch };
        update(next);
    };
    const removeRow = (i: number) => update(rows.filter((_, j) => j !== i));

    const card = (
        <NodeCard
            icon={<Users className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Personnel"}
            badges={
                <>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && rows.length > 0 && (
                        <Badge variant="default" className="text-[10px]">{rows.length} row{rows.length === 1 ? "" : "s"}</Badge>
                    )}
                </>
            }
        >
            <div className="space-y-1.5" contentEditable={false}>
                {rows.map((row, i) => (
                    <div key={i} className="flex items-center gap-1">
                        <select
                            disabled={!isOperator}
                            value={row.user_id}
                            onChange={(e) => setRow(i, { user_id: Number(e.target.value) })}
                            className="h-8 flex-1 rounded border bg-background px-2 text-sm"
                        >
                            {users.map((u) => (
                                <option key={u.id} value={u.id}>{displayName(u)}</option>
                            ))}
                        </select>
                        <select
                            disabled={!isOperator}
                            value={row.role}
                            onChange={(e) => setRow(i, { role: e.target.value as NonSigRole })}
                            className="h-8 w-28 rounded border bg-background px-2 text-sm"
                        >
                            {ROLES.map((r) => (
                                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                        </select>
                        {isOperator && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeRow(i)}
                                className="h-8 w-8 p-0"
                            >
                                <X className="h-3 w-3" />
                            </Button>
                        )}
                    </div>
                ))}
                {rows.length === 0 && (
                    <div className="text-xs italic text-muted-foreground">
                        {isOperator ? "No personnel captured yet." : "Operator adds personnel rows here."}
                    </div>
                )}
                {isOperator && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={addRow}
                        className="h-7 w-full justify-start text-xs text-muted-foreground"
                    >
                        <Plus className="mr-1 h-3 w-3" /> Add personnel
                    </Button>
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>{card}</AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const PersonnelRolesField = Node.create({
    name: "personnelRolesField",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Personnel" },
            required: { default: false },
            min_rows: { default: 1 },
            default_role: { default: "OPERATOR" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="personnel-roles-field"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "personnel-roles-field" }),
            `[PERSONNEL] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_PERSONNEL_ROLES = {
    type: "personnelRolesField",
    attrs: {
        node_id: "seed-personnel-roles-1",
        label: "Operators on the job",
        required: false,
        min_rows: 1,
        default_role: "OPERATOR",
    },
};
