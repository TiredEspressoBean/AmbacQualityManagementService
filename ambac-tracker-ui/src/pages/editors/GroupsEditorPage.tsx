import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useTenantGroups, tenantGroupsOptions } from "@/hooks/useTenantGroups";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Plus, Users } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"TenantGroup">>();

// Default params for prefetch
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
};

// Prefetch function for route loader
export const prefetchGroupsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(tenantGroupsOptions(DEFAULT_LIST_PARAMS));
};

function useGroupsList({
    offset,
    limit,
    ordering,
    search,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    // Note: TenantGroups list endpoint does not support `search` (no DRF search_fields on backend)
    void search;
    const queries: Parameters<typeof useTenantGroups>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    return useTenantGroups(queries);
}

const BLANK = "__blank__";
const csrf = () => ({ headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } });

/** New group (blank, or started from a preset) or a copy of an existing one.
 *  Group admin is change_tenantgroup, as everywhere else (user decision 2026-10-29). */
function GroupDialog({ open, onOpenChange, copyFrom }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    copyFrom: { id: string; name: string } | null;
}) {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [preset, setPreset] = useState<string>(BLANK);
    const { data: presets } = useQuery({
        queryKey: ["presets"],
        queryFn: () => api.api_presets_retrieve(),
        enabled: open && !copyFrom,
    });
    const save = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: async () => {
            const body = { name: name.trim(), description: description.trim() };
            if (copyFrom) return api.api_TenantGroups_clone_create(body, { params: { id: copyFrom.id }, ...csrf() });
            if (preset !== BLANK) return api.api_TenantGroups_from_preset_create({ preset, name: body.name }, csrf());
            return api.api_TenantGroups_create(body, csrf());
        },
        onSuccess: (created) => {
            queryClient.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).toLowerCase().includes("group") });
            toast.success(copyFrom ? `Copied to ${name.trim()}` : `Created ${name.trim()}`);
            onOpenChange(false);
            const id = (created as { id?: string | number } | undefined)?.id;
            if (id != null) navigate({ to: "/editor/groups/$id", params: { id: String(id) } });
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't save the group"),
    });
    const presetList = ((presets as { presets?: Array<{ key: string; name: string }> } | undefined)?.presets ?? []);
    return (
        <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) { setName(""); setDescription(""); setPreset(BLANK); } }}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{copyFrom ? `Copy ${copyFrom.name}` : "New group"}</DialogTitle>
                    <DialogDescription>
                        {copyFrom
                            ? "A new custom group with the same permissions. Members aren't copied."
                            : "A custom group. Start blank and add permissions, or start from a preset's permissions."}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                    <div className="space-y-1">
                        <Label htmlFor="group-name">Name</Label>
                        <Input id="group-name" value={name} onChange={(e) => setName(e.target.value)} />
                    </div>
                    {!copyFrom && (
                        <div className="space-y-1">
                            <Label>Start from</Label>
                            <Select value={preset} onValueChange={setPreset}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={BLANK}>Blank — no permissions</SelectItem>
                                    {presetList.map((p) => (
                                        <SelectItem key={p.key} value={p.key}>{p.name} preset</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    {(copyFrom || preset === BLANK) && (
                        <div className="space-y-1">
                            <Label htmlFor="group-desc">Description</Label>
                            <Textarea id="group-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
                        {copyFrom ? "Copy" : "Create"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

export function GroupsEditorPage() {
    const navigate = useNavigate();
    const canManage = usePermissionSet().has("change_tenantgroup");
    const [dialog, setDialog] = useState<{ copyFrom: { id: string; name: string } | null } | null>(null);

    return (
        <>
        <ModelEditorPage
            title="User Groups"
            modelName="TenantGroups"
            useList={useGroupsList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Newest", value: "-created_at" },
                { label: "Oldest", value: "created_at" },
            ]}
            columns={[
                col({ header: "Name", renderCell: (item) => item.name }),
                col({
                    header: "Type",
                    renderCell: (item) => (
                        <Badge variant={item.is_custom ? "secondary" : "outline"}>
                            {item.is_custom ? "Custom" : item.preset_key || "Preset"}
                        </Badge>
                    ),
                }),
                col({
                    header: "Members",
                    renderCell: (item) => (
                        <Badge variant="outline">
                            {item.member_count ?? 0}
                        </Badge>
                    ),
                }),
                col({
                    header: "Permissions",
                    renderCell: (item) => (
                        <Badge variant="secondary">
                            {item.permission_count ?? 0}
                        </Badge>
                    ),
                }),
            ]}
            extraToolbarContent={canManage ? (
                <Button onClick={() => setDialog({ copyFrom: null })}>
                    <Plus className="h-4 w-4 mr-1" /> New group
                </Button>
            ) : undefined}
            renderActions={(item) => (
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate({ to: "/editor/groups/$id", params: { id: String(item.id) } })}
                        title="View Group Details"
                    >
                        <Users className="h-4 w-4 mr-1" />
                        View
                    </Button>
                    {canManage && (
                        <Button variant="ghost" size="sm" title="Copy this group"
                                onClick={() => setDialog({ copyFrom: { id: String(item.id), name: item.name } })}>
                            <Copy className="h-4 w-4 mr-1" />
                            Copy
                        </Button>
                    )}
                </div>
            )}
            showDetailsLink={false}
        />
        <GroupDialog open={dialog !== null} onOpenChange={(v) => { if (!v) setDialog(null); }}
                     copyFrom={dialog?.copyFrom ?? null} />
        </>
    );
}
