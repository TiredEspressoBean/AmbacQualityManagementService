"use client"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Check, ChevronsUpDown } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { useParams } from "@tanstack/react-router"
import { useInfiniteQuery } from "@tanstack/react-query"

import { api, schemas, type PaginatedUserSelectList } from "@/lib/api/generated"
import { useRetrieveQualityReport } from "@/hooks/useRetrieveQualityReport"
import { useCreateQualityReport } from "@/hooks/useCreateQualityReport"
import { useUpdateQualityReport } from "@/hooks/useUpdateQualityReport"
import { useRetrieveParts } from "@/hooks/useRetrieveParts"
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps"
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments"
import { isFieldRequired } from "@/lib/zod-config"

const STATUS_OPTIONS = schemas.QualityReportStatusEnum.options;

// Use generated schema for validation
const formSchema = schemas.QualityReportsRequest.pick({
    step: true,
    part: true,
    machine: true,
    status: true,
    description: true,
    detected_by: true,
    verified_by: true,
    is_first_piece: true,
    archived: true,
}).extend({
    // Make measurements optional for the form (can be added separately)
    measurements: z.array(z.any()).optional(),
});

type FormValues = z.infer<typeof formSchema>;

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

export default function EditQualityReportFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const qualityReportId = params.id;

    // Fetch quality report data if in edit mode
    const { data: qualityReport } = useRetrieveQualityReport(qualityReportId);

    // Fetch employees for dropdowns
    const { data: employeePages } = useInfiniteQuery<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });
    const employees = employeePages?.pages.flatMap((p) => p.results) ?? [];

    // Search states
    const [partSearch, setPartSearch] = useState("");
    const [stepSearch, setStepSearch] = useState("");
    const [machineSearch, setMachineSearch] = useState("");
    const [detectedBySearch, setDetectedBySearch] = useState("");
    const [verifiedBySearch, setVerifiedBySearch] = useState("");

    // Fetch parts, steps, and equipment for dropdowns
    const { data: partsData } = useRetrieveParts({ limit: 100, search: partSearch });
    const { data: stepsData } = useRetrieveSteps({ limit: 100, search: stepSearch });
    const { data: equipmentData } = useRetrieveEquipments({ limit: 100, search: machineSearch });

    const parts = partsData?.results ?? [];
    const steps = stepsData?.results ?? [];
    const equipment = equipmentData?.results ?? [];

    // Filtered employee lists
    const filteredDetectedBy = employees.filter((emp) =>
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(detectedBySearch.toLowerCase())
    );
    const filteredVerifiedBy = employees.filter((emp) =>
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(verifiedBySearch.toLowerCase())
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            part: undefined,
            step: undefined,
            machine: undefined,
            status: "PENDING",
            description: "",
            detected_by: undefined,
            verified_by: undefined,
            is_first_piece: false,
            archived: false,
            measurements: [],
        },
    });

    // Reset form when quality report data loads in edit mode
    useEffect(() => {
        if (mode === "edit" && qualityReport) {
            form.reset({
                part: qualityReport.part ?? undefined,
                step: qualityReport.step ?? undefined,
                machine: qualityReport.machine ?? undefined,
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
        const submitData = {
            ...values,
            measurements: values.measurements || [],
        };

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
                            const selectedPart = parts.find((p) => p.id === field.value);
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.part}>Part</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selectedPart ? `${selectedPart.ERP_id} - ${selectedPart.part_type_name}` : "Select a part"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={partSearch}
                                                    onValueChange={setPartSearch}
                                                    placeholder="Search parts..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No parts found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {parts.map((p) => (
                                                            <CommandItem
                                                                key={p.id}
                                                                value={p.ERP_id}
                                                                onSelect={() => {
                                                                    form.setValue("part", p.id);
                                                                    setPartSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", p.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {p.ERP_id} - {p.part_type_name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
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
                            const selectedStep = steps.find((s) => s.id === field.value);
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.step}>Process Step</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selectedStep
                                                        ? `${selectedStep.name}${selectedStep.process_name ? ` (${selectedStep.process_name})` : ""}`
                                                        : "Select a step"
                                                    }
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={stepSearch}
                                                    onValueChange={setStepSearch}
                                                    placeholder="Search steps..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No steps found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {steps.map((s) => (
                                                            <CommandItem
                                                                key={s.id}
                                                                value={s.name}
                                                                onSelect={() => {
                                                                    form.setValue("step", s.id);
                                                                    setStepSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", s.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {s.name} {s.process_name && `(${s.process_name})`}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>The process step where inspection occurred</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Machine/Equipment */}
                    <FormField
                        control={form.control}
                        name="machine"
                        render={({ field }) => {
                            const selectedMachine = equipment.find((e) => e.id === field.value);
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Machine/Equipment</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selectedMachine ? selectedMachine.name : "Select equipment (optional)"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={machineSearch}
                                                    onValueChange={setMachineSearch}
                                                    placeholder="Search equipment..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No equipment found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            value="none"
                                                            onSelect={() => {
                                                                form.setValue("machine", undefined);
                                                                setMachineSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", !field.value ? "opacity-100" : "opacity-0")}
                                                            />
                                                            No equipment
                                                        </CommandItem>
                                                        {equipment.map((e) => (
                                                            <CommandItem
                                                                key={e.id}
                                                                value={e.name}
                                                                onSelect={() => {
                                                                    form.setValue("machine", e.id);
                                                                    setMachineSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", e.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {e.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
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
                            const selectedEmployee = employees.find((emp) => emp.id === field.value);
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Detected By</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selectedEmployee
                                                        ? `${selectedEmployee.first_name} ${selectedEmployee.last_name}`
                                                        : "Select inspector"
                                                    }
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={detectedBySearch}
                                                    onValueChange={setDetectedBySearch}
                                                    placeholder="Search employees..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No employees found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {filteredDetectedBy.map((emp) => (
                                                            <CommandItem
                                                                key={emp.id}
                                                                value={`${emp.first_name} ${emp.last_name}`}
                                                                onSelect={() => {
                                                                    form.setValue("detected_by", emp.id);
                                                                    setDetectedBySearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", emp.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {emp.first_name} {emp.last_name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
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
                            const selectedEmployee = employees.find((emp) => emp.id === field.value);
                            return (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Verified By</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selectedEmployee
                                                        ? `${selectedEmployee.first_name} ${selectedEmployee.last_name}`
                                                        : "Select verifier"
                                                    }
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={verifiedBySearch}
                                                    onValueChange={setVerifiedBySearch}
                                                    placeholder="Search employees..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No employees found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {filteredVerifiedBy.map((emp) => (
                                                            <CommandItem
                                                                key={emp.id}
                                                                value={`${emp.first_name} ${emp.last_name}`}
                                                                onSelect={() => {
                                                                    form.setValue("verified_by", emp.id);
                                                                    setVerifiedBySearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", emp.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {emp.first_name} {emp.last_name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
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
                                        checked={field.value}
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
                                        checked={field.value}
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
        </div>
    );
}
