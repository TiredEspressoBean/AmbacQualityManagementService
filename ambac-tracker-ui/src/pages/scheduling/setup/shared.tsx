/** Pieces shared by the scheduling-setup editors (step timings, machine eligibility,
 *  changeovers): row actions, step / machine pickers, and the form-page frame. */
import { useMemo, useState } from "react";
import { Combobox } from "@/components/ui/combobox";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    const [search, setSearch] = useState("");
    const { data, isLoading } = useRetrieveSteps({ limit: 50, is_current_version: true, ...(search ? { search } : {}) });
    const options = useMemo(() => (data?.results ?? []).map((s) => ({
        value: String(s.id), label: s.name, description: s.part_type_name ?? undefined,
    })), [data]);
    return (
        <Combobox value={value || null} onChange={(v) => v && onChange(v)} options={options}
            onSearch={setSearch} loading={isLoading} placeholder={placeholder}
            searchPlaceholder="Search steps…" emptyText="No steps match." disabled={disabled} />
    );
}

export function EquipmentSelect({ value, onChange, disabled }: {
    value: string; onChange: (v: string) => void; disabled?: boolean;
}) {
    const [search, setSearch] = useState("");
    const { data, isLoading } = useRetrieveEquipments({ limit: 50, ...(search ? { search } : {}) });
    const options = useMemo(() => (data?.results ?? []).map((m) => ({
        value: String(m.id), label: m.name, description: m.serial_number || undefined,
    })), [data]);
    return (
        <Combobox value={value || null} onChange={(v) => v && onChange(v)} options={options}
            onSearch={setSearch} loading={isLoading} placeholder="Select a machine"
            searchPlaceholder="Search machines…" emptyText="No machines match." disabled={disabled} />
    );
}

/** Page frame for a create/edit form: back arrow, title, body, save/cancel, then
 *  an optional footer (a record's history) below the buttons. */
export function SetupFormFrame({ title, description, backTo, loading, saving, submitLabel, onSubmit, children, footer }: {
    title: string;
    description: string;
    backTo: string;
    loading: boolean;
    saving: boolean;
    submitLabel: string;
    onSubmit: () => void;
    children: React.ReactNode;
    footer?: React.ReactNode;
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
            {footer}
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
