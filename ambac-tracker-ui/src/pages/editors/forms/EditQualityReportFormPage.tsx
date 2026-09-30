"use client"
import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { Combobox } from "@/components/ui/combobox";
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useForm, type Resolver } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import type { Schema } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { useParams } from "@tanstack/react-router"
import { useInfiniteQuery, infiniteQueryOptions } from "@tanstack/react-query"

import { api, schemas, type PaginatedUserSelectList } from "@/lib/api/generated"
import { useRetrieveQualityReport } from "@/hooks/useRetrieveQualityReport"
import { useCreateQualityReport } from "@/hooks/useCreateQualityReport"
import { useUpdateQualityReport } from "@/hooks/useUpdateQualityReport"
import { useRetrieveParts } from "@/hooks/parts"
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps"
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments"
import { isFieldRequired } from "@/lib/zod-config"

const STATUS_OPTIONS = schemas.QualityReportStatusEnum.options;

// Use generated schema for validation
const formSchema = schemas.QualityReportsRequest.pick({
    step: true,
    part: true,
    production_equipment: true,
    status: true,
    description: true,
    detected_by: true,
    verified_by: true,
    is_first_piece: true,
    archived: true,
}).extend({
    // Optional for the form (measurements are added separately via the DWI
    // flow), but keeping the generated element shape rather than z.any(): as
    // `unknown[]` the payload no longer matched the request type and every
    // submit cast the mismatch away.
    measurements: schemas.QualityReportsRequest.shape.measurements.optional(),
});

// Strict request type from openapi-typescript, plus form-only fields.
// Surfaces upstream API renames as compile errors.
type FormValues = Pick<
    Schema<"QualityReportsRequest">,
    "step" | "part" | "production_equipment" | "status" | "description" | "detected_by" | "verified_by" | "is_first_piece" | "archived"
> & {
    measurements?: Schema<"QualityReportsRequest">["measurements"];
};

// Pre-compute required fields for labels
const required = {
    status: isFieldRequired(formSchema.shape.status),
    part: isFieldRequired(formSchema.shape.part),
    step: isFieldRequired(formSchema.shape.step),
    description: isFieldRequired(formSchema.shape.description),
};

// Status labels for display
const statusLabels: Record<string, string> = {
    PASS: "Pass",
    FAIL: "Fail (NCR)",
    PENDING: "Pending Review",
};

const employeeOptionsInfinite = () =>
    infiniteQueryOptions<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam as number } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

export default function EditQualityReportFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const qualityReportId = params.id;

    // Fetch quality report data if in edit mode
    const { data: qualityReport } = useRetrieveQualityReport(qualityReportId);

    // Fetch employees for dropdowns
    const { data: employeePages } = useInfiniteQuery(employeeOptionsInfinite());
    const employees = employeePages?.pages.flatMap((p) => p.results) ?? [];

    // Search states
    const [partSearch, setPartSearch] = useState("");
    const [stepSearch, setStepSearch] = useState("");
    const [machineSearch, setMachineSearch] = useState("");

    // Fetch parts, steps, and equipment for dropdowns
    const { data: partsData } = useRetrieveParts({ limit: 100, search: partSearch });
    const { data: stepsData } = useRetrieveSteps({ limit: 100, search: stepSearch });
    const { data: equipmentData } = useRetrieveEquipments({ limit: 100, search: machineSearch });

    const parts = partsData?.results ?? [];
    const steps = stepsData?.results ?? [];
    const equipment = equipmentData?.results ?? [];


    const form = useForm<FormValues, any, FormValues>({
        resolver: zodResolver(formSchema) as Resolver<FormValues, any, FormValues>,
        defaultValues: {
            part: "",
            step: "",
            status: "PENDING",
            description: "",
            is_first_piece: false,
            archived: false,
            measurements: [],
        } as FormValues,
    });

    // Reset form when quality report data loads in edit mode
    useEffect(() => {
        if (mode === "edit" && qualityReport) {
            form.reset({
                part: qualityReport.part ?? undefined,
                step: qualityReport.step ?? undefined,
                // Prefill the production machine from the PRODUCTION equipment link.
                production_equipment: qualityReport.equipment_links?.find(
                    (l) => l.role === "PRODUCTION",
                )?.equipment ?? undefined,
                status: qualityReport.status ?? "PENDING",
                description: qualityReport.description ?? "",
                detected_by: qualityReport.detected_by ?? undefined,
                verified_by: qualityReport.verified_by ?? undefined,
                is_first_piece: qualityReport.is_first_piece ?? false,
                archived: qualityReport.archived ?? false,
                measurements: [],
            });
        }
    }, [mode, qualityReport, form]);

    const createQualityReport = useCreateQualityReport();
    const updateQualityReport = useUpdateQualityReport();

    function onSubmit(values: FormValues) {
        // In edit mode `measurements` is never touched by this form (the DWI
        // inline-capture path owns those writes). Sending an empty array here
        // used to clobber the linked MeasurementResults; the backend now
        // discards the field on update, but keep it out of the payload too so
        // the intent is legible.
        const submitData =
            mode === "edit"
                ? { ...values, measurements: undefined }
                : { ...values, measurements: values.measurements || [] };

        if (mode === "edit" && qualityReportId) {
            updateQualityReport.mutate(
                { id: qualityReportId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("Quality Report updated successfully!");
                    },
                    onError: (error) => {
                        console.error("Failed to update quality report:", error);
                        toast.error("Failed to update the quality report.");
                    },
                }
            );
        } else {
            createQualityReport.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Quality Report created successfully!");
                    form.reset();
                },
                onError: (error) => {
                    console.error("Failed to create quality report:", error);
                    toast.error("Failed to create the quality report.");
                },
            });
        }
    }

    return (
        <div>
            <Form {...form}>
                <div className="max-w-3xl mx-auto py-6">
                    <h1 className="text-2xl font-semibold tracking-tight">
                        {mode === "edit" ? "Edit Quality Report" : "Create Quality Report (NCR)"}
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        {mode === "edit"
                            ? `Update details for Quality Report #${qualityReportId ?? ""}`
                            : "Fill out the details below to create a new quality report / NCR."
                        }
                    </p>
                </div>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                    {/* Status */}
                    <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.status}>Status</FormLabel>
                                <Select onValueChange={field.onChange} value={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select the status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {STATUS_OPTIONS.map((status) => (
                                            <SelectItem key={status} value={status}>
                                                {statusLabels[status] ?? status}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    FAIL status indicates a Non-Conformance Report (NCR)
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Part */}
                    <FormField
                        control={form.control}
                        name="part"
                        render={({ field }) => {
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.part}>Part</FormLabel>
                                    <FormControl>
                                        <Combobox
                                            className="w-[300px]"
                                            contentClassName="w-[300px]"
                                            value={field.value || null}
                                            onChange={(v) => v && form.setValue("part", v)}
                                            options={parts.map((p) => ({ value: p.id, label: p.ERP_id, ...(p.part_type_name ? { description: p.part_type_name } : {}) }))}
                                            onSearch={setPartSearch}
                                            placeholder="Select a part"
                                            searchPlaceholder="Search parts..."
                                            emptyText="No parts found."
                                        />
                                    </FormControl>
                                    <FormDescription>The part being inspected</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Step */}
                    <FormField
                        control={form.control}
                        name="step"
                        render={({ field }) => {
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.step}>Process Step</FormLabel>
                                    <FormControl>
                                        <Combobox
                                            className="w-[300px]"
                                            contentClassName="w-[300px]"
                                            value={field.value || null}
                                            onChange={(v) => v && form.setValue("step", v)}
                                            options={steps.map((s) => ({ value: s.id, label: s.name, ...(s.part_type_name ? { description: s.part_type_name } : {}) }))}
                                            onSearch={setStepSearch}
                                            placeholder="Select a step"
                                            searchPlaceholder="Search steps..."
                                            emptyText="No steps found."
                                        />
                                    </FormControl>
                                    <FormDescription>The process step where inspection occurred</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Machine/Equipment */}
                    <FormField
                        control={form.control}
                        name="production_equipment"
                        render={({ field }) => {
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Machine/Equipment</FormLabel>
                                    <FormControl>
                                        <Combobox
                                            className="w-[300px]"
                                            contentClassName="w-[300px]"
                                            value={field.value || null}
                                            onChange={(v) => form.setValue("production_equipment", v ?? undefined)}
                                            options={equipment.map((e) => ({ value: e.id, label: e.name }))}
                                            onSearch={setMachineSearch}
                                            clearLabel="No equipment"
                                            placeholder="Select equipment (optional)"
                                            searchPlaceholder="Search equipment..."
                                            emptyText="No equipment found."
                                        />
                                    </FormControl>
                                    <FormDescription>Equipment used during inspection (optional)</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Description */}
                    <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.description}>Description</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe the inspection findings, any defects observed, or quality notes..."
                                        className="min-h-[100px]"
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormDescription>Detailed description of inspection findings</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Detected By */}
                    <FormField
                        control={form.control}
                        name="detected_by"
                        render={({ field }) => {
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Detected By</FormLabel>
                                    <FormControl>
                                        <Combobox
                                            className="w-[300px]"
                                            contentClassName="w-[300px]"
                                            value={field.value == null ? null : String(field.value)}
                                            onChange={(v) => v && form.setValue("detected_by", Number(v))}
                                            options={employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` }))}
                                            placeholder="Select inspector"
                                            searchPlaceholder="Search employees..."
                                            emptyText="No employees found."
                                        />
                                    </FormControl>
                                    <FormDescription>Person who performed the inspection</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Verified By */}
                    <FormField
                        control={form.control}
                        name="verified_by"
                        render={({ field }) => {
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Verified By</FormLabel>
                                    <FormControl>
                                        <Combobox
                                            className="w-[300px]"
                                            contentClassName="w-[300px]"
                                            value={field.value == null ? null : String(field.value)}
                                            onChange={(v) => v && form.setValue("verified_by", Number(v))}
                                            options={employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` }))}
                                            placeholder="Select verifier"
                                            searchPlaceholder="Search employees..."
                                            emptyText="No employees found."
                                        />
                                    </FormControl>
                                    <FormDescription>Person who verified the inspection</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* First Piece Inspection */}
                    <FormField
                        control={form.control}
                        name="is_first_piece"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value ?? false}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>First Piece Inspection</FormLabel>
                                    <FormDescription>
                                        Mark this as a first article inspection (FAI) for setup verification
                                    </FormDescription>
                                    <FormMessage />
                                </div>
                            </FormItem>
                        )}
                    />

                    {/* Archived */}
                    <FormField
                        control={form.control}
                        name="archived"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value ?? false}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>Archived</FormLabel>
                                    <FormDescription>
                                        Archive this report (hidden from default views)
                                    </FormDescription>
                                    <FormMessage />
                                </div>
                            </FormItem>
                        )}
                    />

                    <Button type="submit" disabled={createQualityReport.isPending || updateQualityReport.isPending}>
                        {createQualityReport.isPending || updateQualityReport.isPending
                            ? (mode === "edit" ? "Saving..." : "Creating...")
                            : "Submit"
                        }
                    </Button>
                </form>
            </Form>
            {mode === "edit" && qualityReportId && (
                <div className="max-w-3xl mx-auto py-6">
                    <RecordHistoryCard endpoint="QualityReports" id={qualityReportId} model="qualityreports" />
                </div>
            )}
        </div>
    );
}
