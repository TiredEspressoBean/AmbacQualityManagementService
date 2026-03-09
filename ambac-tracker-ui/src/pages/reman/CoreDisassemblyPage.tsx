import { useState } from "react";
import { useParams, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { api } from "@/lib/api/generated";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { format } from "date-fns";
import { ArrowLeft, Plus, CheckCircle, Trash2, Package, Loader2, Wrench } from "lucide-react";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";

function getConditionVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}

export function CoreDisassemblyPage() {
    const { id } = useParams({ from: '/reman/cores/$id/disassembly' });
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [harvestDialogOpen, setHarvestDialogOpen] = useState(false);
    const [newComponent, setNewComponent] = useState({
        component_type: "",
        position: "",
        condition_grade: "B",
        condition_notes: "",
        original_part_number: "",
    });

    const { data: core, isLoading, error } = useRetrieveCore(id);
    const { data: componentsData, refetch: refetchComponents } = useRetrieveHarvestedComponents({ core: id });
    const { data: partTypesData } = useRetrievePartTypes({ limit: 100 });

    const partTypes = partTypesData?.results ?? [];
    const components = componentsData?.results ?? [];

    // Start disassembly mutation
    const startDisassemblyMutation = useMutation({
        mutationFn: () => api.api_Cores_start_disassembly_create({ id }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["core", id] });
            queryClient.invalidateQueries({ queryKey: ["cores"] });
            toast.success("Disassembly started");
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to start disassembly");
        },
    });

    // Complete disassembly mutation
    const completeDisassemblyMutation = useMutation({
        mutationFn: () => api.api_Cores_complete_disassembly_create({ id }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["core", id] });
            queryClient.invalidateQueries({ queryKey: ["cores"] });
            toast.success("Disassembly completed");
            navigate({ to: `/reman/cores/${id}` });
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to complete disassembly");
        },
    });

    // Harvest component mutation
    const harvestComponentMutation = useMutation({
        mutationFn: (data: typeof newComponent) =>
            api.api_HarvestedComponents_create({
                core: id,
                ...data,
            }),
        onSuccess: () => {
            refetchComponents();
            queryClient.invalidateQueries({ queryKey: ["cores"] });
            setHarvestDialogOpen(false);
            setNewComponent({
                component_type: "",
                position: "",
                condition_grade: "B",
                condition_notes: "",
                original_part_number: "",
            });
            toast.success("Component harvested");
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to harvest component");
        },
    });

    // Scrap component mutation
    const scrapComponentMutation = useMutation({
        mutationFn: ({ componentId, reason }: { componentId: string; reason: string }) =>
            api.api_HarvestedComponents_scrap_create({ id: componentId, reason }),
        onSuccess: () => {
            refetchComponents();
            toast.success("Component scrapped");
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to scrap component");
        },
    });

    // Accept to inventory mutation
    const acceptToInventoryMutation = useMutation({
        mutationFn: (componentId: string) =>
            api.api_HarvestedComponents_accept_to_inventory_create({ id: componentId }),
        onSuccess: (data: any) => {
            refetchComponents();
            toast.success(`Component accepted. Part ID: ${data.part_erp_id}`);
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to accept component");
        },
    });

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (error || !core) {
        return (
            <div className="text-center py-8">
                <p className="text-destructive">Failed to load core</p>
                <Button variant="outline" className="mt-4" asChild>
                    <Link to="/reman/cores">Back to Cores</Link>
                </Button>
            </div>
        );
    }

    const canStartDisassembly = core.status === 'RECEIVED';
    const isInDisassembly = core.status === 'IN_DISASSEMBLY';
    const isDisassembled = core.status === 'DISASSEMBLED';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link to={`/reman/cores/${id}`}>
                            <ArrowLeft className="h-4 w-4" />
                        </Link>
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <Wrench className="h-6 w-6" />
                            Disassembly: {core.core_number}
                        </h1>
                        <p className="text-muted-foreground">
                            {core.core_type_name} - {components.length} components harvested
                        </p>
                    </div>
                </div>
                <div className="flex gap-2">
                    {canStartDisassembly && (
                        <Button
                            onClick={() => startDisassemblyMutation.mutate()}
                            disabled={startDisassemblyMutation.isPending}
                        >
                            {startDisassemblyMutation.isPending && (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            )}
                            Start Disassembly
                        </Button>
                    )}
                    {isInDisassembly && (
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="default">
                                    <CheckCircle className="mr-2 h-4 w-4" />
                                    Complete Disassembly
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Complete Disassembly?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        This will mark the core as fully disassembled.
                                        You have harvested {components.length} components.
                                        Are you sure you want to complete?
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                        onClick={() => completeDisassemblyMutation.mutate()}
                                    >
                                        Complete
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    )}
                </div>
            </div>

            {/* Status Banner */}
            {canStartDisassembly && (
                <Card className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
                    <CardContent className="py-4">
                        <p className="text-yellow-800 dark:text-yellow-200">
                            This core is ready for disassembly. Click "Start Disassembly" to begin harvesting components.
                        </p>
                    </CardContent>
                </Card>
            )}

            {isDisassembled && (
                <Card className="border-green-500 bg-green-50 dark:bg-green-950">
                    <CardContent className="py-4">
                        <p className="text-green-800 dark:text-green-200">
                            Disassembly completed on {core.disassembly_completed_at && format(new Date(core.disassembly_completed_at), "PPP")}
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Harvested Components */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Package className="h-5 w-5" />
                            Harvested Components ({components.length})
                        </CardTitle>
                        <CardDescription>
                            Components extracted from this core
                        </CardDescription>
                    </div>
                    {isInDisassembly && (
                        <Dialog open={harvestDialogOpen} onOpenChange={setHarvestDialogOpen}>
                            <DialogTrigger asChild>
                                <Button>
                                    <Plus className="mr-2 h-4 w-4" />
                                    Harvest Component
                                </Button>
                            </DialogTrigger>
                            <DialogContent>
                                <DialogHeader>
                                    <DialogTitle>Harvest Component</DialogTitle>
                                    <DialogDescription>
                                        Record a component extracted from this core
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label>Component Type *</Label>
                                        <Select
                                            value={newComponent.component_type}
                                            onValueChange={(val) =>
                                                setNewComponent((prev) => ({ ...prev, component_type: val }))
                                            }
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select component type" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {partTypes.map((pt: any) => (
                                                    <SelectItem key={pt.id} value={pt.id}>
                                                        {pt.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label>Position</Label>
                                            <Input
                                                placeholder="e.g., Cyl 1, Position A"
                                                value={newComponent.position}
                                                onChange={(e) =>
                                                    setNewComponent((prev) => ({ ...prev, position: e.target.value }))
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Condition Grade *</Label>
                                            <Select
                                                value={newComponent.condition_grade}
                                                onValueChange={(val) =>
                                                    setNewComponent((prev) => ({ ...prev, condition_grade: val }))
                                                }
                                            >
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="A">Grade A - Excellent</SelectItem>
                                                    <SelectItem value="B">Grade B - Good</SelectItem>
                                                    <SelectItem value="C">Grade C - Fair</SelectItem>
                                                    <SelectItem value="scrap">Scrap</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Original Part Number</Label>
                                        <Input
                                            placeholder="OEM part number if readable"
                                            value={newComponent.original_part_number}
                                            onChange={(e) =>
                                                setNewComponent((prev) => ({
                                                    ...prev,
                                                    original_part_number: e.target.value,
                                                }))
                                            }
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Condition Notes</Label>
                                        <Textarea
                                            placeholder="Describe the condition..."
                                            value={newComponent.condition_notes}
                                            onChange={(e) =>
                                                setNewComponent((prev) => ({
                                                    ...prev,
                                                    condition_notes: e.target.value,
                                                }))
                                            }
                                        />
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button
                                        variant="outline"
                                        onClick={() => setHarvestDialogOpen(false)}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        onClick={() => harvestComponentMutation.mutate(newComponent)}
                                        disabled={
                                            !newComponent.component_type ||
                                            harvestComponentMutation.isPending
                                        }
                                    >
                                        {harvestComponentMutation.isPending && (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        )}
                                        Harvest
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    )}
                </CardHeader>
                <CardContent>
                    {components.length === 0 ? (
                        <p className="text-center py-8 text-muted-foreground">
                            No components harvested yet. Click "Harvest Component" to begin.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Type</TableHead>
                                    <TableHead>Position</TableHead>
                                    <TableHead>Condition</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Part ID</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {components.map((component: any) => (
                                    <TableRow key={component.id}>
                                        <TableCell className="font-medium">
                                            {component.component_type_name}
                                        </TableCell>
                                        <TableCell>{component.position || "—"}</TableCell>
                                        <TableCell>
                                            <Badge variant={getConditionVariant(component.condition_grade)}>
                                                Grade {component.condition_grade}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {component.is_scrapped ? (
                                                <Badge variant="destructive">Scrapped</Badge>
                                            ) : component.component_part ? (
                                                <Badge variant="default">In Inventory</Badge>
                                            ) : (
                                                <Badge variant="secondary">Pending</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {component.component_part_erp_id || "—"}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {!component.is_scrapped && !component.component_part && (
                                                <div className="flex justify-end gap-2">
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() =>
                                                            acceptToInventoryMutation.mutate(component.id)
                                                        }
                                                        disabled={acceptToInventoryMutation.isPending}
                                                    >
                                                        <Package className="mr-1 h-3 w-3" />
                                                        Accept
                                                    </Button>
                                                    <AlertDialog>
                                                        <AlertDialogTrigger asChild>
                                                            <Button size="sm" variant="destructive">
                                                                <Trash2 className="mr-1 h-3 w-3" />
                                                                Scrap
                                                            </Button>
                                                        </AlertDialogTrigger>
                                                        <AlertDialogContent>
                                                            <AlertDialogHeader>
                                                                <AlertDialogTitle>Scrap Component?</AlertDialogTitle>
                                                                <AlertDialogDescription>
                                                                    This component will be marked as scrapped and cannot be added to inventory.
                                                                </AlertDialogDescription>
                                                            </AlertDialogHeader>
                                                            <AlertDialogFooter>
                                                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                                <AlertDialogAction
                                                                    onClick={() =>
                                                                        scrapComponentMutation.mutate({
                                                                            componentId: component.id,
                                                                            reason: "Condition not suitable for reuse",
                                                                        })
                                                                    }
                                                                >
                                                                    Scrap
                                                                </AlertDialogAction>
                                                            </AlertDialogFooter>
                                                        </AlertDialogContent>
                                                    </AlertDialog>
                                                </div>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default CoreDisassemblyPage;
