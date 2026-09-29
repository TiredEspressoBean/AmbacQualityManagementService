/** Pieces shared by the scheduling-setup editors (step timings, machine eligibility,
 *  changeovers): row actions, step / machine pickers, and the form-page frame. */
import { useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";

export const ATTENTION_LABEL: Record<string, string> = {
    full: "Full attention",
    load_unload: "Load / unload only",
    unattended: "Unattended",
};

export const AFFINITY_LABEL: Record<string, string> = {
    eligible: "Eligible",
    preferred: "Preferred",
    dialed_in: "Dialed in (proven best)",
};

/** Same defaults as ModelEditorPage: platform staff bypass, and unknown means allowed. */
export function useAllows() {
    const { has, isLoading } = usePermissionSet();
    const { data: authUser } = useAuthUser();
    const isStaff = (authUser as { is_staff?: boolean } | undefined)?.is_staff ?? false;
    return (codename: string) => isLoading || isStaff || has(codename);
}

export function RowActions({ label, editTo, onDelete, canEdit, canDelete }: {
    label: string;
    editTo: string;
    onDelete: () => void;
    canEdit: boolean;
    canDelete: boolean;
}) {
    const navigate = useNavigate();
    return (
        <>
            {canEdit && (
                <Button size="icon" variant="ghost" aria-label={`Edit ${label}`}
                    onClick={() => navigate({ to: editTo })}>
                    <Pencil className="h-4 w-4" />
                </Button>
            )}
            {canDelete && (
                <Button size="icon" variant="ghost" className="text-destructive" aria-label={`Delete ${label}`}
                    onClick={() => {
                        if (window.confirm(`Delete ${label}? The scheduler stops using it.`)) onDelete();
                    }}>
                    <Trash2 className="h-4 w-4" />
                </Button>
            )}
        </>
    );
}

/** Toast the most specific message a DRF error body carries. */
export function toastApiError(err: unknown, fields: string[] = []) {
    const body = apiErrorBody(err);
    const message =
        fields.map((f) => apiErrorField(body, f)).find(Boolean) ??
        apiErrorField(body, "detail") ??
        apiErrorField(body, "non_field_errors") ??
        (err as Error)?.message ??
        "unknown error";
    toast.error(message);
}

/** Step names repeat across processes, so each option carries its part type. */
export function StepSelect({ value, onChange, placeholder = "Select a step", disabled }: {
    value: string; onChange: (v: string) => void; placeholder?: string; disabled?: boolean;
}) {
    const { data } = useRetrieveSteps({ limit: 500 });
    const steps = useMemo(() => data?.results ?? [], [data]);
    return (
        <Select value={value} onValueChange={(v) => v && onChange(v)} {...(disabled ? { disabled } : {})}>
            <SelectTrigger><SelectValue placeholder={placeholder} /></SelectTrigger>
            <SelectContent>
                {steps.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                        {s.name}{s.part_type_name ? ` · ${s.part_type_name}` : ""}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

export function EquipmentSelect({ value, onChange, disabled }: {
    value: string; onChange: (v: string) => void; disabled?: boolean;
}) {
    const { data } = useRetrieveEquipments({ limit: 500 });
    const machines = useMemo(() => data?.results ?? [], [data]);
    return (
        <Select value={value} onValueChange={(v) => v && onChange(v)} {...(disabled ? { disabled } : {})}>
            <SelectTrigger><SelectValue placeholder="Select a machine" /></SelectTrigger>
            <SelectContent>
                {machines.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                        {m.name}{m.serial_number ? ` · ${m.serial_number}` : ""}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

/** Page frame for a create/edit form: back arrow, title, body, save/cancel. */
export function SetupFormFrame({ title, description, backTo, loading, saving, submitLabel, onSubmit, children }: {
    title: string;
    description: string;
    backTo: string;
    loading: boolean;
    saving: boolean;
    submitLabel: string;
    onSubmit: () => void;
    children: React.ReactNode;
}) {
    const navigate = useNavigate();
    if (loading) {
        return (
            <div className="mx-auto max-w-3xl p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 w-64 rounded bg-muted" />
                    <div className="h-64 rounded bg-muted" />
                </div>
            </div>
        );
    }
    return (
        <div className="mx-auto max-w-3xl space-y-6 p-6 pb-24">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" aria-label="Back" onClick={() => navigate({ to: backTo })}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">{title}</h1>
                    <p className="text-muted-foreground">{description}</p>
                </div>
            </div>
            {children}
            <div className="flex gap-3">
                <Button onClick={onSubmit} disabled={saving} className="flex-1">
                    {saving ? "Saving…" : submitLabel}
                </Button>
                <Button variant="ghost" onClick={() => navigate({ to: backTo })} disabled={saving}>
                    Cancel
                </Button>
            </div>
        </div>
    );
}

/** A minutes field: blank reads as 0, anything negative or non-numeric is refused. */
export function parseMinutes(raw: string, label: string): number | null {
    const trimmed = raw.trim();
    if (trimmed === "") return 0;
    const n = Number(trimmed);
    if (!Number.isFinite(n) || n < 0) {
        toast.error(`${label} must be a number of minutes, 0 or more`);
        return null;
    }
    return n;
}
