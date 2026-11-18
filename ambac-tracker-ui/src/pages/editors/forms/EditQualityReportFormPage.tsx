"use client"
import { apiErrorMessage } from "@/lib/api/describeApiError"
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
import { useNavigate, useParams, useSearch } from "@tanstack/react-router"
import { useInfiniteQuery, infiniteQueryOptions, useQuery, useQueryClient } from "@tanstack/react-query"
import { invalidateAfterNcrChange } from "@/hooks/ncrs"

import { api, schemas, type PaginatedUserSelectList } from "@/lib/api/generated"
import { useRetrieveQualityReport } from "@/hooks/useRetrieveQualityReport"
import { useCreateQualityReport } from "@/hooks/useCreateQualityReport"
import { useUpdateQualityReport } from "@/hooks/useUpdateQualityReport"
import { useRetrieveParts } from "@/hooks/parts"
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps"
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments"
import { isFieldRequired } from "@/lib/zod-config"
import { useAuthUser } from "@/hooks/useAuthUser"

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
    FAIL: "Fail",
    PENDING: "Pending Review",
    // Refused by the server except for a core in rebuild at a check with planned repairs.
    REPAIR: "Needs repair (rebuild checks only)",
};

const employeeOptionsInfinite = () =>
    infiniteQueryOptions<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam as number } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

export default function EditQualityReportFormPage() {
    const queryClient = useQueryClient()
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const mode = params.id ? "edit" : "create";
    // `?part=&step=` prefill a new report (the operator home's "Flag").
    const prefill = useSearch({ strict: false }) as { part?: string; step?: string };
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
    const { data: equipmentData } = useRetrieveEquipments({ limit: 100, search: machineSearch });

    // A prefilled part / step may be outside the first page of options; fetch it so the
    // picker shows its name rather than a blank.
    const { data: prefillPart } = useQuery({
        queryKey: ["parts", "detail", prefill.part],
        queryFn: () => api.api_Parts_retrieve({ params: { id: prefill.part! } }),
        enabled: mode === "create" && !!prefill.part,
    });
    const { data: prefillStep } = useQuery({
        queryKey: ["steps", "detail", prefill.step],
        queryFn: () => api.api_Steps_retrieve({ params: { id: prefill.step! } }),
        enabled: mode === "create" && !!prefill.step,
    });
    const parts = [
        ...(prefillPart && !(partsData?.results ?? []).some((x) => x.id === prefillPart.id) ? [prefillPart] : []),
        ...(partsData?.results ?? []),
    ];
    const equipment = equipmentData?.results ?? [];


    // The chosen part: its process limits the step picker, and its current step is
    // where it's being inspected unless said otherwise.
    const [chosenPartId, setChosenPartId] = useState<string | undefined>(mode === "create" ? prefill.part : undefined);
    const { data: chosenPart } = useQuery({
        queryKey: ["parts", "detail", chosenPartId],
        queryFn: () => api.api_Parts_retrieve({ params: { id: chosenPartId! } }),
        enabled: !!chosenPartId,
    });
    const { data: stepsData } = useRetrieveSteps({
        limit: 100, search: stepSearch,
        ...(chosenPart?.process ? { process_memberships__process: String(chosenPart.process) } : {}),
    });

    const steps = [
        ...(prefillStep && !(stepsData?.results ?? []).some((x) => x.id === prefillStep.id) ? [prefillStep] : []),
        ...(stepsData?.results ?? []),
    ];
    // Its current step, named even when it isn't in the first page of steps.
    const partStepOption = chosenPart?.step && !steps.some((x) => x.id === chosenPart.step)
        ? [{ value: String(chosenPart.step), label: chosenPart.step_name ?? "Current step" }] : [];

    const form = useForm<FormValues, any, FormValues>({
        resolver: zodResolver(formSchema) as Resolver<FormValues, any, FormValues>,
        defaultValues: {
            part: mode === "create" ? prefill.part ?? "" : "",
            step: mode === "create" ? prefill.step ?? "" : "",
            status: "PENDING",
            description: "",
            is_first_piece: false,
            archived: false,
            measurements: [],
        } as FormValues,
    });

    // Whoever records it found it, unless they say otherwise: Detected By starts as them.
    const { data: me } = useAuthUser();
    useEffect(() => {
        if (mode === "create" && me?.pk != null && form.getValues("detected_by") == null) {
            form.setValue("detected_by", Number(me.pk));
        }
    }, [mode, me?.pk, form]);
    // A part chosen: inspected at its current step, unless a step was handed over.
    useEffect(() => {
        if (mode === "create" && chosenPart?.step && !(prefill.step && chosenPart.id === prefill.part)) {
            form.setValue("step", String(chosenPart.step));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- once per part chosen
    }, [chosenPart?.id]);

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
                        toast.success("Inspection record updated");
                        // A Fail puts the part on an NCR and holds it: those screens too.
                        if (values.status === "FAIL") void invalidateAfterNcrChange(queryClient);
                    },
                    onError: (error) => {
                        console.error("Failed to update quality report:", error);
                        toast.error(apiErrorMessage(error) ?? "Failed to update the quality report.");
                    },
                }
            );
        } else {
            createQualityReport.mutate(submitData, {
                onSuccess: async (created) => {
                    form.reset();
                    setChosenPartId(undefined);
                    if (values.status !== "FAIL") { toast.success("Inspection recorded"); return; }
                    void invalidateAfterNcrChange(queryClient);
                    // A Fail is on an NCR now (its open one, or a new one): say which, and go there.
                    const saved = await api.api_QualityReports_retrieve({ params: { id: String(created.id) } }).catch(() => null);
                    if (saved?.ncr) {
                        toast.success(`Inspection recorded · on ${saved.ncr_number}`, {
                            action: { label: "Open NCR", onClick: () => navigate({ to: "/quality/ncrs/$ncrId", params: { ncrId: String(saved.ncr) } }) },
                        });
                    } else {
                        toast.success("Inspection recorded");
                    }
                },
                onError: (error) => {
                    console.error("Failed to create quality report:", error);
                    toast.error(apiErrorMessage(error) ?? "Failed to create the quality report.");
                },
            });
        }
    }

    return (
        <div>
            <Form {...form}>
                <div className="max-w-3xl mx-auto py-6">
                    <h1 className="text-2xl font-semibold tracking-tight">
                        {mode === "edit" ? "Edit Inspection Record" : "Record Inspection"}
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        {mode === "edit"
                            ? `Update details for inspection record #${qualityReportId ?? ""}`
                            : "Record an inspection result. A Fail puts the part on an NCR — its open one, or a new one."
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
                                    A Fail holds the part and puts it on an NCR, where its decision is made.
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
                                            onChange={(v) => { if (v) { form.setValue("part", v); setChosenPartId(v); } }}
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
                                            options={[...partStepOption, ...steps.map((s) => ({ value: s.id, label: s.name, ...(s.part_type_name ? { description: s.part_type_name } : {}) }))]}
                                            onSearch={setStepSearch}
                                            placeholder="Select a step"
                                            searchPlaceholder="Search steps..."
                                            emptyText="No steps found."
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Where it was inspected — the part's current step unless you change it. The list is its process's steps.
                                    </FormDescription>
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
                                            options={[
                                                // The signed-in person (the default), when not on the loaded page.
                                                ...(mode === "create" && me && !employees.some((e) => String(e.id) === String(me.pk))
                                                    ? [{ value: String(me.pk), label: me.full_name || me.email || "Me" }]
                                                    : []),
                                                ...employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` })),
                                            ]}
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
