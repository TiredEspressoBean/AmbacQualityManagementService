"use client"
import {useEffect} from "react";
import {toast} from "sonner";
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

// Use generated schema - error messages handled by global error map
const formSchema = schemas.PartTypesRequest.pick({
    name: true,
    ID_prefix: true,
    ERP_id: true,
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
            itar_controlled: false,
            eccn: "",
            usml_category: "",
        },
    });

    useEffect(() => {
        if (mode === "edit" && partType) {
            form.reset({
                name: partType.name ?? "",
                ID_prefix: partType.ID_prefix ?? "",
                ERP_id: partType.ERP_id ?? "",
                itar_controlled: partType.itar_controlled ?? false,
                eccn: partType.eccn ?? "",
                usml_category: partType.usml_category ?? "",
            });
        }
    }, [mode, partType, form]);

    const createPartType = useCreatePartType();
    const updatePartType = useUpdatePartType();

    function onSubmit(values: FormValues) {
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

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Bill of Materials</CardTitle>
                    <ReportButton
                        reportType="bom_report"
                        label="BOM Report"
                        params={chosen ? {id: chosen.id} : null}
                    />
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
                    </div>
                )}
            </CardHeader>
            <CardContent>
                {listLoading ? (
                    <p className="text-sm text-muted-foreground">Loading BOMs…</p>
                ) : !chosen ? (
                    <p className="text-sm text-muted-foreground">No released BOM for this part type.</p>
                ) : detailLoading ? (
                    <p className="text-sm text-muted-foreground">Loading lines…</p>
                ) : lines.length === 0 ? (
                    <p className="text-sm text-muted-foreground">This BOM has no lines.</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Find #</TableHead>
                                <TableHead>Component</TableHead>
                                <TableHead>Qty</TableHead>
                                <TableHead>UoM</TableHead>
                                <TableHead>Optional</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {lines.map((line) => (
                                <TableRow key={line.id}>
                                    <TableCell>{line.find_number || "—"}</TableCell>
                                    <TableCell className="font-medium">
                                        {line.component_type_name || "—"}
                                    </TableCell>
                                    <TableCell>{line.quantity}</TableCell>
                                    <TableCell>{line.unit_of_measure || "—"}</TableCell>
                                    <TableCell>{line.is_optional ? "Yes" : "No"}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </CardContent>
        </Card>
    );
}
