/**
 * Station detail — the "what's AT this work center" hub (work-center Phase 0
 * mapping tooling). Three tabs:
 *   Steps     — routing steps stationed here; assign/unassign in bulk
 *               (PATCH Steps.work_center — a non-versioning routing edit).
 *   Equipment — machines/gauges placed here (WorkCenter.equipment M2M —
 *               non-versioning placement edit).
 *   People    — user memberships (eligibility) with primary-station star.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Star, X } from "lucide-react";

import { api } from "@/lib/api/generated";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
    Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";

type StationLite = {
    id: string;
    code: string;
    name: string;
    kind?: string;
    equipment?: string[];
    equipment_names?: string[];
};

function useInvalidate() {
    const qc = useQueryClient();
    return () => {
        qc.invalidateQueries({ queryKey: ["work-centers"] });
        qc.invalidateQueries({ queryKey: ["station-steps"] });
        qc.invalidateQueries({ queryKey: ["station-members"] });
    };
}

/* ---------------------------------- Steps --------------------------------- */

function StepsTab({ station }: { station: StationLite }) {
    const invalidate = useInvalidate();
    const [pickerOpen, setPickerOpen] = useState(false);
    // Step→station mapping is a routing edit on Steps — authoring tier.
    const canEdit = usePermissionSet().has("change_steps");

    // Steps stationed here (current versions only — the list endpoint spans versions).
    const { data: herePage, isLoading } = useQuery({
        queryKey: ["station-steps", station.id] as const,
        queryFn: () => api.api_Steps_list({
            queries: { work_center: station.id, limit: 200 },
        } as never) as Promise<any>,
    });
    const here: any[] = ((herePage?.results ?? []) as any[]).filter(
        (s) => s.is_current_version !== false);

    // Every current step, for the assign picker (shows its present station).
    const { data: allPage } = useQuery({
        queryKey: ["station-steps", "all"] as const,
        enabled: pickerOpen,
        queryFn: () => api.api_Steps_list({ queries: { limit: 500 } } as never) as Promise<any>,
    });
    const assignable: any[] = ((allPage?.results ?? []) as any[]).filter(
        (s) => s.is_current_version !== false && s.work_center !== station.id);

    const patchStep = useMutation({
        mutationFn: ({ id, work_center }: { id: string; work_center: string | null }) =>
            api.api_Steps_partial_update({ work_center } as never, { params: { id } } as never),
        onSuccess: () => invalidate(),
        onError: () => toast.error("Couldn't update the step's station."),
    });

    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                Routing steps that run at this station. Assigning is a routing edit — it
                doesn't create a new step version.
            </p>
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : here.length === 0 ? (
                <p className="text-sm text-muted-foreground">No steps stationed here.</p>
            ) : (
                <div className="space-y-1">
                    {here.map((s) => (
                        <div key={s.id} className="flex items-center gap-2 rounded border px-2 py-1.5 text-sm">
                            <span className="min-w-0 flex-1 truncate font-medium">{s.name}</span>
                            <Badge variant="outline" className="text-[10px]">{s.step_type}</Badge>
                            {s.part_type_name && (
                                <span className="hidden text-xs text-muted-foreground sm:inline">{s.part_type_name}</span>
                            )}
                            {canEdit && (
                                <button
                                    type="button"
                                    title="Unassign from this station"
                                    className="rounded p-0.5 text-muted-foreground hover:text-destructive"
                                    onClick={() => patchStep.mutate({ id: String(s.id), work_center: null })}
                                >
                                    <X className="h-3.5 w-3.5" />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {canEdit && (<Popover open={pickerOpen} onOpenChange={setPickerOpen}>
                <PopoverTrigger asChild>
                    <Button variant="outline" size="sm">
                        <Plus className="mr-1 h-4 w-4" /> Assign steps…
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-96 p-0" align="start">
                    <Command>
                        <CommandInput placeholder="Search steps…" />
                        <CommandList>
                            <CommandEmpty>No other steps.</CommandEmpty>
                            <CommandGroup>
                                {assignable.map((s) => (
                                    <CommandItem
                                        key={s.id}
                                        value={`${s.name} ${s.part_type_name ?? ""}`}
                                        // Stays open — assign several in one pass.
                                        onSelect={() => patchStep.mutate({ id: String(s.id), work_center: station.id })}
                                    >
                                        <span className="min-w-0 flex-1 truncate">{s.name}</span>
                                        <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                                            {s.work_center_name ?? "Unmapped"}
                                        </span>
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>)}
        </div>
    );
}

/* -------------------------------- Equipment ------------------------------- */

function EquipmentTab({ station }: { station: StationLite }) {
    const invalidate = useInvalidate();
    const [pickerOpen, setPickerOpen] = useState(false);
    // Equipment placement edits the WorkCenter itself — WC authoring tier.
    const canEdit = usePermissionSet().has("change_workcenter");

    // Current placement comes from the row we were handed; refetch keeps it live.
    const { data: wc } = useQuery({
        queryKey: ["work-centers", "detail", station.id] as const,
        queryFn: () => api.api_WorkCenters_retrieve({ params: { id: station.id } } as never) as Promise<any>,
    });
    const placedIds: string[] = (wc?.equipment ?? station.equipment ?? []).map(String);
    const placedNames: string[] = wc?.equipment_names ?? station.equipment_names ?? [];

    const { data: allEquip } = useQuery({
        queryKey: ["equipment", "station-picker"] as const,
        enabled: pickerOpen,
        queryFn: () => api.api_Equipment_list({ queries: { limit: 500 } } as never) as Promise<any>,
    });
    const candidates: any[] = ((allEquip?.results ?? []) as any[]).filter(
        (e) => !placedIds.includes(String(e.id)));

    const setEquipment = useMutation({
        mutationFn: (equipment: string[]) =>
            api.api_WorkCenters_partial_update({ equipment } as never, { params: { id: station.id } } as never),
        onSuccess: () => invalidate(),
        onError: () => toast.error("Couldn't update the station's equipment."),
    });

    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                Machines and gauges physically at this station. Placement is operational
                master data — editing it doesn't version the work center.
            </p>
            {placedIds.length === 0 ? (
                <p className="text-sm text-muted-foreground">No equipment placed here.</p>
            ) : (
                <div className="space-y-1">
                    {placedIds.map((id, i) => (
                        <div key={id} className="flex items-center gap-2 rounded border px-2 py-1.5 text-sm">
                            <span className="min-w-0 flex-1 truncate">{placedNames[i] ?? id}</span>
                            {canEdit && (
                                <button
                                    type="button"
                                    title="Remove from this station"
                                    className="rounded p-0.5 text-muted-foreground hover:text-destructive"
                                    onClick={() => setEquipment.mutate(placedIds.filter((x) => x !== id))}
                                >
                                    <X className="h-3.5 w-3.5" />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {canEdit && (<Popover open={pickerOpen} onOpenChange={setPickerOpen}>
                <PopoverTrigger asChild>
                    <Button variant="outline" size="sm">
                        <Plus className="mr-1 h-4 w-4" /> Add equipment…
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="start">
                    <Command>
                        <CommandInput placeholder="Search equipment…" />
                        <CommandList>
                            <CommandEmpty>Nothing left to add.</CommandEmpty>
                            <CommandGroup>
                                {candidates.map((e) => (
                                    <CommandItem
                                        key={e.id}
                                        value={e.name}
                                        onSelect={() => setEquipment.mutate([...placedIds, String(e.id)])}
                                    >
                                        <span className="min-w-0 flex-1 truncate">{e.name}</span>
                                        {e.status && (
                                            <span className="ml-2 shrink-0 text-xs text-muted-foreground">{e.status}</span>
                                        )}
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>)}
        </div>
    );
}

/* --------------------------------- People --------------------------------- */

function PeopleTab({ station }: { station: StationLite }) {
    const invalidate = useInvalidate();
    const [pickerOpen, setPickerOpen] = useState(false);
    // Memberships are access administration — team-access (manager) tier.
    const { hasAny } = usePermissionSet();
    const canEdit = hasAny("add_userworkcentermembership", "change_userworkcentermembership");

    const { data: page, isLoading } = useQuery({
        queryKey: ["station-members", station.id] as const,
        queryFn: () => api.api_UserWorkCenterMemberships_list({
            queries: { work_center: station.id, limit: 200 },
        } as never) as Promise<any>,
    });
    const members: any[] = (page?.results ?? []) as any[];
    const memberUserIds = new Set(members.map((m) => m.user));

    const { data: usersPage } = useQuery({
        queryKey: ["users", "station-picker"] as const,
        enabled: pickerOpen,
        queryFn: () => api.api_User_list({ queries: { limit: 500 } } as never) as Promise<any>,
    });
    const candidates: any[] = ((usersPage?.results ?? []) as any[]).filter(
        (u) => !memberUserIds.has(u.id));

    const addMember = useMutation({
        mutationFn: (userId: number) =>
            api.api_UserWorkCenterMemberships_create({
                user: userId, work_center: station.id, is_primary: false,
            } as never),
        onSuccess: () => invalidate(),
        onError: () => toast.error("Couldn't add the member."),
    });
    const removeMember = useMutation({
        mutationFn: (id: string) =>
            api.api_UserWorkCenterMemberships_destroy(undefined as never, { params: { id } } as never),
        onSuccess: () => invalidate(),
        onError: () => toast.error("Couldn't remove the member."),
    });
    const setPrimary = useMutation({
        mutationFn: (id: string) =>
            api.api_UserWorkCenterMemberships_set_primary_create(
                undefined as never, { params: { id } } as never),
        onSuccess: () => invalidate(),
        onError: () => toast.error("Couldn't set primary."),
    });

    const label = (m: any) =>
        m.user_name ?? m.user_full_name ?? m.user_email ?? m.username ?? String(m.user);

    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                Who is eligible to work at this station. The star marks a user's primary
                (home) station — it drives their operator-home default and dispatch steering.
            </p>
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : members.length === 0 ? (
                <p className="text-sm text-muted-foreground">No members yet.</p>
            ) : (
                <div className="space-y-1">
                    {members.map((m) => (
                        <div key={m.id} className="flex items-center gap-2 rounded border px-2 py-1.5 text-sm">
                            <span className="min-w-0 flex-1 truncate">{label(m)}</span>
                            {canEdit ? (
                                <button
                                    type="button"
                                    title={m.is_primary ? "Primary station" : "Make primary"}
                                    className="rounded p-0.5"
                                    onClick={() => !m.is_primary && setPrimary.mutate(String(m.id))}
                                >
                                    <Star className={`h-4 w-4 ${m.is_primary
                                        ? "fill-amber-400 text-amber-400"
                                        : "text-muted-foreground hover:text-amber-400"}`} />
                                </button>
                            ) : (
                                m.is_primary && <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                            )}
                            {canEdit && (
                                <button
                                    type="button"
                                    title="Remove membership"
                                    className="rounded p-0.5 text-muted-foreground hover:text-destructive"
                                    onClick={() => removeMember.mutate(String(m.id))}
                                >
                                    <X className="h-3.5 w-3.5" />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {canEdit && (<Popover open={pickerOpen} onOpenChange={setPickerOpen}>
                <PopoverTrigger asChild>
                    <Button variant="outline" size="sm">
                        <Plus className="mr-1 h-4 w-4" /> Add member…
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="start">
                    <Command>
                        <CommandInput placeholder="Search users…" />
                        <CommandList>
                            <CommandEmpty>No users to add.</CommandEmpty>
                            <CommandGroup>
                                {candidates.map((u) => (
                                    <CommandItem
                                        key={u.id}
                                        value={`${u.first_name ?? ""} ${u.last_name ?? ""} ${u.email ?? ""} ${u.username ?? ""}`}
                                        onSelect={() => addMember.mutate(u.id)}
                                    >
                                        <span className="min-w-0 flex-1 truncate">
                                            {(u.first_name || u.last_name)
                                                ? `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim()
                                                : (u.email ?? u.username)}
                                        </span>
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>)}
        </div>
    );
}

/* --------------------------------- Dialog --------------------------------- */

export function StationDialog({
    station, open, onOpenChange,
}: {
    station: StationLite | null;
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    // Reset the tab when a different station opens.
    const key = station?.id ?? "none";
    const initialTab = useMemo(() => "steps", [key]);  // eslint-disable-line react-hooks/exhaustive-deps

    if (!station) return null;
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <span className="font-mono text-sm text-muted-foreground">{station.code}</span>
                        {station.name}
                    </DialogTitle>
                    <DialogDescription>
                        What's at this station — its routing steps, equipment, and people.
                    </DialogDescription>
                </DialogHeader>
                <Tabs defaultValue={initialTab} key={key}>
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="steps">Steps</TabsTrigger>
                        <TabsTrigger value="equipment">Equipment</TabsTrigger>
                        <TabsTrigger value="people">People</TabsTrigger>
                    </TabsList>
                    <TabsContent value="steps"><StepsTab station={station} /></TabsContent>
                    <TabsContent value="equipment"><EquipmentTab station={station} /></TabsContent>
                    <TabsContent value="people"><PeopleTab station={station} /></TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}

export default StationDialog;
