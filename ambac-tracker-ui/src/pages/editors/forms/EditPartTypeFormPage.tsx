"use client"
import {useEffect, useState} from "react";
import {toast} from "sonner";
import {Plus, Pencil, Trash2} from "lucide-react";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {useQuery} from "@tanstack/react-query";
import {Button} from "@/components/ui/button";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage} from "@/components/ui/form";
import {Input} from "@/components/ui/input";
import {Checkbox} from "@/components/ui/checkbox";
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";
import {Badge} from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {useParams} from "@tanstack/react-router";

import {useRetrievePartType} from "@/hooks/useRetrievePartType";
import {useCreatePartType} from "@/hooks/useCreatePartType";
import {useUpdatePartType} from "@/hooks/useUpdatePartType";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";
import {api, schemas} from "@/lib/api/generated";
import {ReportButton} from "@/components/reports/ReportButton";
import {isFieldRequired} from "@/lib/zod-config";
import {usePermissionSet} from "@/hooks/useMyPermissions";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {BomLineDialog, type BomLine} from "@/components/bom/BomLineDialog";
import {useCreateBom, useReleaseBom, useCreateBomRevision, useDeleteBomLine} from "@/hooks/useBom";
import {useRetrieveSteps} from "@/hooks/useRetrieveSteps";

// Use generated schema - error messages handled by global error map
const formSchema = schemas.PartTypesRequest.pick({
    name: true,
    ID_prefix: true,
    ERP_id: true,
    can_make: true,
    can_buy: true,
    purchase_lead_time_days: true,
    itar_controlled: true,
    eccn: true,
    usml_category: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    ID_prefix: isFieldRequired(formSchema.shape.ID_prefix),
    ERP_id: isFieldRequired(formSchema.shape.ERP_id),
    itar_controlled: isFieldRequired(formSchema.shape.itar_controlled),
    eccn: isFieldRequired(formSchema.shape.eccn),
    usml_category: isFieldRequired(formSchema.shape.usml_category),
};

export default function PartTypeFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? "edit" : "create";
    const partTypeId = params.id;

    const {data: partType} = useRetrievePartType({params: {id: partTypeId!}}, {enabled: mode === "edit" && !!partTypeId});

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema), defaultValues: {
            name: "",
            ID_prefix: "",
            ERP_id: "",
            can_make: true,
            can_buy: false,
            purchase_lead_time_days: null,
            itar_controlled: false,
            eccn: "",
            usml_category: "",
        },
    });

    // Preferred-supplier combobox (nullable FK) — kept out of RHF like the
    // material/fixture forms.
    const [supplierId, setSupplierId] = useState<string | null>(null);
    const {data: companiesPage} = useQuery({
        queryKey: ["companies", "part-type-supplier-picker"] as const,
        queryFn: () => api.api_Companies_list({queries: {limit: 500, ordering: "name"}} as never) as Promise<{
            results?: Array<{ id: string | number; name: string }>
        }>,
    });
    const suppliers = (companiesPage?.results ?? []).map((c) => ({id: String(c.id), name: c.name}));

    useEffect(() => {
        if (mode === "edit" && partType) {
            form.reset({
                name: partType.name ?? "",
                ID_prefix: partType.ID_prefix ?? "",
                ERP_id: partType.ERP_id ?? "",
                can_make: (partType as { can_make?: boolean }).can_make ?? true,
                can_buy: (partType as { can_buy?: boolean }).can_buy ?? false,
                purchase_lead_time_days:
                    (partType as { purchase_lead_time_days?: number | null }).purchase_lead_time_days ?? null,
                itar_controlled: partType.itar_controlled ?? false,
                eccn: partType.eccn ?? "",
                usml_category: partType.usml_category ?? "",
            });
            const ps = (partType as { preferred_supplier?: string | null }).preferred_supplier;
            setSupplierId(ps != null ? String(ps) : null);
        }
    }, [mode, partType, form]);

    const createPartType = useCreatePartType();
    const updatePartType = useUpdatePartType();

    function onSubmit(raw: FormValues) {
        const values = {...raw, preferred_supplier: supplierId} as FormValues;
        if (mode === "edit" && partTypeId) {
            updatePartType.mutate({id: partTypeId, data: values}, {
                onSuccess: () => {
                    toast.success("Part Type updated successfully!");
                }, onError: (error) => {
                    console.error("Failed to update part type:", error);
                    toast.error("Failed to update the part type.");
                },
            });
        } else {
            createPartType.mutate(values, {
                onSuccess: () => {
                    toast.success("Part Type created successfully!");
                    form.reset();
                }, onError: (error) => {
                    console.error("Failed to create part type:", error);
                    toast.error("Failed to create the part type.");
                },
            });
        }
    }

    return (<div>
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                <FormField
                    control={form.control}
                    name="name"
                    render={({field}) => (<FormItem>
                        <FormLabel required={required.name}>Name</FormLabel>
                        <FormControl>
                            <Input placeholder="e.g. Fuel Rail" {...field} />
                        </FormControl>
                        <FormDescription>The name of this type of part</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
                />

                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="ID_prefix"
                        render={({field}) => (<FormItem>
                            <FormLabel required={required.ID_prefix}>ERP ID Prefix</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. FR" {...field} value={field.value ?? ""} />
                            </FormControl>
                            <FormDescription>Prefix for ERP-generated part numbers</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="ERP_id"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.ERP_id}>ERP ID</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. SV852-8R" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>Unique ERP identifier</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                {/* Sourcing — make/buy is an attribute of the part, not an identity:
                    a dual-sourced part (made normally, bought when slammed) sets both. */}
                <div className="space-y-3 rounded-md border p-4">
                    <div>
                        <h3 className="text-sm font-medium">Sourcing</h3>
                        <p className="text-sm text-muted-foreground">
                            How this part is obtained. Both may be checked for a dual-sourced part.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="can_make"
                            render={({field}) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                    <FormControl>
                                        <Checkbox checked={field.value ?? true} onCheckedChange={field.onChange}/>
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Made in-house</FormLabel>
                                        <FormDescription>Produced via a process; shortages spawn child work orders</FormDescription>
                                    </div>
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="can_buy"
                            render={({field}) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                    <FormControl>
                                        <Checkbox checked={field.value ?? false} onCheckedChange={field.onChange}/>
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Purchased</FormLabel>
                                        <FormDescription>Bought from a supplier; received lots run the incoming-quality gates</FormDescription>
                                    </div>
                                </FormItem>
                            )}
                        />
                    </div>
                    {form.watch("can_buy") && (
                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="purchase_lead_time_days"
                                render={({field}) => (
                                    <FormItem>
                                        <FormLabel>Purchase lead time (days)</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number" min={0} placeholder="e.g. 14"
                                                value={field.value ?? ""}
                                                onChange={(e) => field.onChange(
                                                    e.target.value === "" ? null : Number(e.target.value))}
                                            />
                                        </FormControl>
                                        <FormDescription>Drives the order-by date on the sourcing report</FormDescription>
                                        <FormMessage/>
                                    </FormItem>
                                )}
                            />
                            <FormItem>
                                <FormLabel>Preferred supplier</FormLabel>
                                <select
                                    className="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs"
                                    value={supplierId ?? ""}
                                    onChange={(e) => setSupplierId(e.target.value || null)}
                                >
                                    <option value="">None</option>
                                    {suppliers.map((s) => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                                <FormDescription>Default supplier when this part is bought</FormDescription>
                            </FormItem>
                        </div>
                    )}
                </div>

                <FormField
                    control={form.control}
                    name="itar_controlled"
                    render={({field}) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                            <FormControl>
                                <Checkbox
                                    checked={field.value ?? false}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>ITAR Controlled</FormLabel>
                                <FormDescription>
                                    This part type is subject to ITAR export controls
                                </FormDescription>
                            </div>
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="eccn"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.eccn}>ECCN</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. 9A003.a" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>Export Control Classification Number</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="usml_category"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.usml_category}>USML Category</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. IV(h)" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>US Munitions List category</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <Button type="submit" disabled={createPartType.isPending || updatePartType.isPending}>
                    {mode === "edit" ? updatePartType.isPending ? "Saving..." : "Save Changes" : createPartType.isPending ? "Creating..." : "Create Part Type"}
                </Button>
            </form>
        </Form>
        {mode === "edit" && partTypeId && (
            <div className="max-w-3xl mx-auto py-6">
                <BomPanel partTypeId={partTypeId} />
            </div>)}
        {mode === "edit" && partTypeId && (

            <div className="max-w-3xl mx-auto py-6">
                <h3 className="text-lg font-semibold">Attach Documents</h3>
                <DocumentUploader objectId={partTypeId} contentType="parttypes"/>
            </div>)}
    </div>);
}

// ---------------------------------------------------------------------------
// Bill of Materials panel — read-only view of the part type's BOM.
//   * lists BOMs for the part type, picks the RELEASED one (highest revision),
//     else falls back to the latest BOM regardless of status;
//   * fetches the chosen BOM's detail (with nested lines) to render the table.
// ---------------------------------------------------------------------------

type BomListItem = z.infer<typeof schemas.BOMList>;
type BomDetail = z.infer<typeof schemas.BOM>;

function pickBom(boms: BomListItem[]): BomListItem | undefined {
    if (boms.length === 0) return undefined;
    // Highest revision first (revisions are short strings, e.g. "A", "B", "10").
    const byRevisionDesc = (a: BomListItem, b: BomListItem) =>
        (b.revision ?? "").localeCompare(a.revision ?? "", undefined, { numeric: true });
    // Prefer an editable DRAFT (that's what you'd be working on), then the
    // effective RELEASED, then whatever's latest.
    const draft = boms.filter((b) => b.status === "DRAFT").sort(byRevisionDesc);
    if (draft.length > 0) return draft[0];
    const released = boms.filter((b) => b.status === "RELEASED").sort(byRevisionDesc);
    if (released.length > 0) return released[0];
    return [...boms].sort(byRevisionDesc)[0];
}

function BomPanel({partTypeId}: {partTypeId: string}) {
    const {data: bomList, isLoading: listLoading} = useQuery({
        queryKey: ["BOMs", "list", {part_type: partTypeId}] as const,
        queryFn: () =>
            api.api_BOMs_list({queries: {part_type: partTypeId, limit: 100}}) as Promise<
                z.infer<typeof schemas.PaginatedBOMListList>
            >,
    });

    const chosen = pickBom(bomList?.results ?? []);

    const {data: bom, isLoading: detailLoading} = useQuery({
        queryKey: ["BOMs", "detail", chosen?.id] as const,
        queryFn: () =>
            api.api_BOMs_retrieve({params: {id: chosen!.id}}) as Promise<BomDetail>,
        enabled: !!chosen?.id,
    });

    const lines = bom?.lines ?? [];
    // BOM authoring is change-control tier: status gates *which* BOM is
    // editable (DRAFT only); the perm gates *who* sees authoring controls.
    const canAuthor = usePermissionSet().hasAny("add_bom", "change_bom", "change_bomline");
    const isDraft = chosen?.status === "DRAFT" && canAuthor;

    // The assembly's own process steps — the ops a line can be "consumed at".
    const {data: stepsData} = useRetrieveSteps({ part_type: partTypeId, limit: 500 } as never);
    const steps = (stepsData?.results ?? [])
        .filter((s) => s?.id)
        .map((s) => ({ id: String(s.id), name: s.name as string }));

    // Mutations + dialog state for inline authoring.
    const createBom = useCreateBom();
    const releaseBom = useReleaseBom();
    const createRevision = useCreateBomRevision();
    const deleteLine = useDeleteBomLine();

    const [lineDialogOpen, setLineDialogOpen] = useState(false);
    const [editingLine, setEditingLine] = useState<BomLine | null>(null);
    const [deletingLineId, setDeletingLineId] = useState<string | null>(null);

    const openAddLine = () => { setEditingLine(null); setLineDialogOpen(true); };
    const openEditLine = (line: BomLine) => { setEditingLine(line); setLineDialogOpen(true); };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Bill of Materials</CardTitle>
                    <div className="flex items-center gap-2">
                        {/* Lifecycle action depends on the chosen BOM's status. */}
                        {!chosen && !listLoading && canAuthor && (
                            <Button size="sm" onClick={() => createBom.mutate(partTypeId)} disabled={createBom.isPending}>
                                <Plus className="mr-1 h-4 w-4" /> Create BOM
                            </Button>
                        )}
                        {isDraft && (
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => chosen && releaseBom.mutate(String(chosen.id))}
                                disabled={releaseBom.isPending || lines.length === 0}
                                title={lines.length === 0 ? "Add at least one line first" : "Release for production"}
                            >
                                Release
                            </Button>
                        )}
                        {chosen && chosen.status !== "DRAFT" && canAuthor && (
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => createRevision.mutate(String(chosen.id))}
                                disabled={createRevision.isPending}
                                title="Start an editable draft copy"
                            >
                                New revision
                            </Button>
                        )}
                        <ReportButton
                            reportType="bom_report"
                            label="BOM Report"
                            params={chosen ? {id: chosen.id} : null}
                        />
                    </div>
                </div>
                {chosen && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground pt-1">
                        <span>Rev {chosen.revision}</span>
                        <span>·</span>
                        <Badge variant={chosen.status === "RELEASED" ? "default" : "secondary"}>
                            {chosen.status ?? "—"}
                        </Badge>
                        <span>·</span>
                        <span>{chosen.line_count} line{chosen.line_count === 1 ? "" : "s"}</span>
                        {canAuthor && !isDraft && chosen.status === "RELEASED" && (
                            <span className="italic">· released BOMs are read-only — use “New revision” to edit</span>
                        )}
                    </div>
                )}
            </CardHeader>
            <CardContent>
                {listLoading ? (
                    <p className="text-sm text-muted-foreground">Loading BOMs…</p>
                ) : !chosen ? (
                    <p className="text-sm text-muted-foreground">
                        No BOM yet for this part type. Create one to list the components it's built from.
                    </p>
                ) : detailLoading ? (
                    <p className="text-sm text-muted-foreground">Loading lines…</p>
                ) : (
                    <>
                        {lines.length === 0 ? (
                            <p className="text-sm text-muted-foreground">
                                {isDraft ? "This draft has no lines yet — add the first component." : "This BOM has no lines."}
                            </p>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Find #</TableHead>
                                        <TableHead>Component</TableHead>
                                        <TableHead>Source</TableHead>
                                        <TableHead>Qty</TableHead>
                                        <TableHead>UoM</TableHead>
                                        <TableHead>Consumed at</TableHead>
                                        <TableHead>Optional</TableHead>
                                        {isDraft && <TableHead className="w-20 text-right">Edit</TableHead>}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {lines.map((line) => {
                                        // A line is EITHER an in-house component_type (MAKE) or a
                                        // purchased material (BUY) — show whichever it carries.
                                        const isBuy = line.source === "BUY";
                                        const label = isBuy
                                            ? line.material_name
                                            : line.component_type_name;
                                        return (
                                            <TableRow key={line.id}>
                                                <TableCell>{line.find_number || "—"}</TableCell>
                                                <TableCell className="font-medium">{label || "—"}</TableCell>
                                                <TableCell>
                                                    <Badge variant={isBuy ? "outline" : "secondary"}>
                                                        {isBuy ? "Buy" : "Make"}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>{line.quantity}</TableCell>
                                                <TableCell>{line.unit_of_measure || "—"}</TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {line.consumed_at_step_name || "Whole assembly"}
                                                </TableCell>
                                                <TableCell>{line.is_optional ? "Yes" : "No"}</TableCell>
                                                {isDraft && (
                                                    <TableCell className="text-right">
                                                        <Button variant="ghost" size="icon" title="Edit line"
                                                            onClick={() => openEditLine(line as BomLine)}>
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button variant="ghost" size="icon" className="text-destructive"
                                                            title="Remove line" onClick={() => setDeletingLineId(String(line.id))}>
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </TableCell>
                                                )}
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        )}

                        {isDraft && (
                            <Button variant="outline" size="sm" className="mt-3" onClick={openAddLine}>
                                <Plus className="mr-1 h-4 w-4" /> Add line
                            </Button>
                        )}
                    </>
                )}
            </CardContent>

            {/* Line create/edit dialog (DRAFT only) */}
            {chosen && (
                <BomLineDialog
                    open={lineDialogOpen}
                    onOpenChange={setLineDialogOpen}
                    bomId={String(chosen.id)}
                    line={editingLine}
                    steps={steps}
                />
            )}

            {/* Delete-line confirm */}
            <AlertDialog open={!!deletingLineId} onOpenChange={(o) => !o && setDeletingLineId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remove this line?</AlertDialogTitle>
                        <AlertDialogDescription>
                            It will be removed from this draft BOM. This can't be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => {
                                if (deletingLineId) deleteLine.mutate(deletingLineId, {onSettled: () => setDeletingLineId(null)});
                            }}
                        >
                            Remove
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    );
}
