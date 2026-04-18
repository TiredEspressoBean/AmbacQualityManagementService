import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2, GripVertical, ChevronUp, ChevronDown, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { useListMilestoneTemplates } from "@/hooks/useListMilestoneTemplates";

type Milestone = {
    id: string;
    name: string;
    customer_display_name: string;
    display_name: string;
    display_order: number;
    description: string;
    is_active: boolean;
    template: string;
};

type MilestoneTemplate = {
    id: string;
    name: string;
    description: string;
    is_default: boolean;
    milestones: Milestone[];
};

function MilestoneRow({
    milestone,
    isFirst,
    isLast,
    onMove,
    onUpdate,
    onDelete,
}: {
    milestone: Milestone;
    isFirst: boolean;
    isLast: boolean;
    onMove: (direction: "up" | "down") => void;
    onUpdate: (field: string, value: any) => void;
    onDelete: () => void;
}) {
    return (
        <div className="flex items-center gap-2 py-2 border-b last:border-0">
            {/* Order controls */}
            <div className="flex flex-col">
                <Button
                    variant="ghost" size="icon" className="h-5 w-5"
                    onClick={() => onMove("up")} disabled={isFirst}
                >
                    <ChevronUp className="h-3 w-3" />
                </Button>
                <Button
                    variant="ghost" size="icon" className="h-5 w-5"
                    onClick={() => onMove("down")} disabled={isLast}
                >
                    <ChevronDown className="h-3 w-3" />
                </Button>
            </div>

            {/* Order number */}
            <span className="text-xs text-muted-foreground w-6 text-center">
                {milestone.display_order + 1}
            </span>

            {/* Name */}
            <Input
                value={milestone.name}
                onChange={(e) => onUpdate("name", e.target.value)}
                className="flex-1 h-8 text-sm"
                placeholder="Internal name"
            />

            {/* Display name */}
            <Input
                value={milestone.customer_display_name}
                onChange={(e) => onUpdate("customer_display_name", e.target.value)}
                className="flex-1 h-8 text-sm"
                placeholder="Customer display name (optional)"
            />

            {/* Active toggle */}
            <div className="flex items-center gap-1">
                <Switch
                    checked={milestone.is_active}
                    onCheckedChange={(checked) => onUpdate("is_active", checked)}
                    className="scale-75"
                />
                <span className="text-xs text-muted-foreground w-12">
                    {milestone.is_active ? "Active" : "Inactive"}
                </span>
            </div>

            {/* Delete */}
            <Button
                variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive"
                onClick={onDelete}
            >
                <Trash2 className="h-3.5 w-3.5" />
            </Button>
        </div>
    );
}

export function MilestonesEditorPage() {
    const queryClient = useQueryClient();
    const { data: templates, isLoading } = useListMilestoneTemplates();
    const [saving, setSaving] = useState(false);

    // Handle both paginated ({results: [...]}) and unpaginated ([...]) responses
    const rawData = templates as any;
    const templatesList: MilestoneTemplate[] = Array.isArray(rawData)
        ? rawData
        : rawData?.results ?? [];

    // Ensure milestones is always an array on each template
    const safeTemplates = templatesList.map(t => ({
        ...t,
        milestones: Array.isArray(t.milestones) ? t.milestones : [],
    }));

    const updateMilestone = useMutation({
        mutationFn: ({ id, data }: { id: string; data: any }) =>
            api.api_Milestones_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["milestoneTemplates"] }),
    });

    const createMilestone = useMutation({
        mutationFn: (data: any) =>
            api.api_Milestones_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["milestoneTemplates"] });
            toast.success("Milestone added");
        },
    });

    const deleteMilestone = useMutation({
        mutationFn: (id: string) =>
            api.api_Milestones_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["milestoneTemplates"] });
            toast.success("Milestone removed");
        },
    });

    const handleUpdate = async (milestone: Milestone, field: string, value: any) => {
        try {
            await updateMilestone.mutateAsync({ id: milestone.id, data: { [field]: value } });
        } catch {
            toast.error("Failed to update milestone");
        }
    };

    const handleMove = async (template: MilestoneTemplate, milestone: Milestone, direction: "up" | "down") => {
        const sorted = [...template.milestones].sort((a, b) => a.display_order - b.display_order);
        const idx = sorted.findIndex(m => m.id === milestone.id);
        const swapIdx = direction === "up" ? idx - 1 : idx + 1;
        if (swapIdx < 0 || swapIdx >= sorted.length) return;

        const other = sorted[swapIdx];
        try {
            setSaving(true);
            await updateMilestone.mutateAsync({ id: milestone.id, data: { display_order: other.display_order } });
            await updateMilestone.mutateAsync({ id: other.id, data: { display_order: milestone.display_order } });
        } catch {
            toast.error("Failed to reorder");
        } finally {
            setSaving(false);
        }
    };

    const handleAdd = async (template: MilestoneTemplate) => {
        const maxOrder = template.milestones.reduce((max, m) => Math.max(max, m.display_order), -1);
        try {
            await createMilestone.mutateAsync({
                template: template.id,
                name: "New Milestone",
                customer_display_name: "",
                display_order: maxOrder + 1,
                description: "",
                is_active: true,
            } as any);
        } catch {
            toast.error("Failed to add milestone");
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await deleteMilestone.mutateAsync(id);
        } catch {
            toast.error("Failed to delete milestone");
        }
    };

    if (isLoading) {
        return (
            <div className="container mx-auto p-6 max-w-3xl">
                <Skeleton className="h-8 w-48 mb-6" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-3xl">
            {/* Header */}
            <div className="mb-6">
                <Link to="/Edit" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Data Management
                </Link>
                <h1 className="text-2xl font-bold">Order Milestones</h1>
                <p className="text-sm text-muted-foreground">
                    Define the business stages orders pass through. Shown as a progress bar on the customer portal.
                </p>
            </div>

            {safeTemplates.length === 0 ? (
                /* Empty state */
                <Card>
                    <CardContent className="py-12 text-center">
                        <p className="text-muted-foreground mb-4">No milestone templates yet</p>
                        <p className="text-sm text-muted-foreground mb-4">
                            Milestones are created automatically when you connect a CRM integration,
                            or you can create them manually.
                        </p>
                        {/* TODO: Add "Create Template" button when manual creation is implemented */}
                    </CardContent>
                </Card>
            ) : (
                safeTemplates.map((template) => {
                    const sorted = [...template.milestones].sort((a, b) => a.display_order - b.display_order);
                    return (
                        <Card key={template.id} className="mb-6">
                            <CardHeader className="pb-2">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle className="text-lg">{template.name}</CardTitle>
                                        {template.description && (
                                            <CardDescription>{template.description}</CardDescription>
                                        )}
                                    </div>
                                    {template.is_default && (
                                        <Badge variant="secondary">Default</Badge>
                                    )}
                                </div>
                                {/* Column headers */}
                                <div className="flex items-center gap-2 pt-3 text-xs text-muted-foreground border-b pb-2">
                                    <div className="w-[52px]" /> {/* Order controls + number */}
                                    <span className="flex-1">Internal Name</span>
                                    <span className="flex-1">Display Name</span>
                                    <span className="w-[76px]">Active</span>
                                    <span className="w-7" /> {/* Delete */}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-0">
                                {sorted.map((milestone, idx) => (
                                    <MilestoneRow
                                        key={milestone.id}
                                        milestone={milestone}
                                        isFirst={idx === 0}
                                        isLast={idx === sorted.length - 1}
                                        onMove={(dir) => handleMove(template, milestone, dir)}
                                        onUpdate={(field, value) => handleUpdate(milestone, field, value)}
                                        onDelete={() => handleDelete(milestone.id)}
                                    />
                                ))}
                                <Button
                                    variant="outline" size="sm" className="mt-3 w-full"
                                    onClick={() => handleAdd(template)}
                                    disabled={createMilestone.isPending}
                                >
                                    {createMilestone.isPending
                                        ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                        : <Plus className="h-4 w-4 mr-1" />
                                    }
                                    Add Milestone
                                </Button>
                            </CardContent>
                        </Card>
                    );
                })
            )}
        </div>
    );
}
