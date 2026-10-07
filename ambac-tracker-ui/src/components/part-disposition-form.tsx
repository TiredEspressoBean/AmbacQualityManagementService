import { MultiPicker } from "@/components/ui/multi-picker";
import { Combobox } from "@/components/ui/combobox";
import * as React from "react";
import {Button} from "@/components/ui/button";
import {toast} from "sonner";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {api, schemas, type PaginatedUserSelectList} from "@/lib/api/generated";
import {isFieldRequired} from "@/lib/zod-config";
import {useInfiniteQuery, infiniteQueryOptions} from "@tanstack/react-query";
import {useQualityReports} from "@/hooks/useQualityReports";
import {useRetrieveParts} from "@/hooks/parts";
import {cn, getCookie} from "@/lib/utils";
import {Popover, PopoverContent, PopoverTrigger,} from "@/components/ui/popover";
import {Textarea} from "@/components/ui/textarea";
import {Input} from "@/components/ui/input";
import {Checkbox} from "@/components/ui/checkbox";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Collapsible, CollapsibleContent, CollapsibleTrigger} from "@/components/ui/collapsible";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,} from "@/components/ui/form";
import { Calendar as CalendarIcon, ChevronDown, Loader2, AlertTriangle, ExternalLink } from "lucide-react";
import {format} from "date-fns";
import {Calendar} from "@/components/ui/calendar";
import {Alert, AlertDescription, AlertTitle} from "@/components/ui/alert";
import {Link} from "@tanstack/react-router";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader";
import {useRetrieveContentTypes} from "@/hooks/useRetrieveContentTypes";

// Use generated schema for disposition form
const formSchema = schemas.QuarantineDispositionRequest.pick({
    current_state: true,
    disposition_type: true,
    severity: true,
    assigned_to: true,
    description: true,
    resolution_notes: true,
    resolution_performed_by: true,
    containment_action: true,
    containment_completed: true,
    containment_performed_by: true,
    requires_customer_approval: true,
    customer_approval_received: true,
    customer_approval_reference: true,
    customer_approval_date: true,
}).extend({
    // Add relationship fields not in base schema
    part: z.string().nullable(),
    quality_reports: z.array(z.string()),
});

type FormValues = z.infer<typeof formSchema>;

const required = {
    current_state: isFieldRequired(formSchema.shape.current_state),
    disposition_type: isFieldRequired(formSchema.shape.disposition_type),
    severity: isFieldRequired(formSchema.shape.severity),
};

// Label maps for enums with custom display text
const currentStateLabels: Record<string, string> = {
    OPEN: "Open",
    IN_PROGRESS: "In Progress",
    CLOSED: "Closed",
};

const dispositionTypeLabels: Record<string, string> = {
    REWORK: "Rework",
    REPAIR: "Repair (AS9100)",
    SCRAP: "Scrap",
    USE_AS_IS: "Use As Is",
    RETURN_TO_SUPPLIER: "Return to Supplier",
};

const severityLabels: Record<string, string> = {
    CRITICAL: "Critical - Safety/Regulatory Impact",
    MAJOR: "Major - Functional Impact",
    MINOR: "Minor - Cosmetic Only",
};

const employeeOptionsInfiniteOptions = () =>
    infiniteQueryOptions<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam as number } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

export default function PartDispositionForm({part, disposition, onClose}: { part: any; disposition?: any; onClose?: () => void }) {
    const [partSearch, setPartSearch] = React.useState("");
    const [qualityReportSearch, setQualityReportSearch] = React.useState("");
    // Collapsible state for containment section - expanded by default for critical
    const [containmentOpen, setContainmentOpen] = React.useState(disposition?.severity === "CRITICAL");

    const {data: employeePages, isLoading: employeesLoading} = useInfiniteQuery(employeeOptionsInfiniteOptions());

    const employees = employeePages?.pages.flatMap((p) => p.results) ?? [];

    // Get content type for QuarantineDisposition (needed for document upload)
    const { data: contentTypes } = useRetrieveContentTypes({});
    const dispositionContentType = contentTypes?.find(
        (ct: { id: number; app_label: string; model: string }) => ct.model === "quarantinedisposition" && ct.app_label === "Tracker"
    );

    const {data: partsData} = useRetrieveParts({limit: 100, search: partSearch});
    const {data: qualityReportsData} = useQualityReports({limit: 100, search: qualityReportSearch});

    const parts = partsData?.results ?? [];
    const qualityReports = qualityReportsData?.results ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema), defaultValues: {
            part: disposition?.part ?? part?.id,
            current_state: disposition?.current_state ?? "OPEN",
            disposition_type: disposition?.disposition_type,
            severity: disposition?.severity ?? "MAJOR",
            assigned_to: disposition?.assigned_to,
            description: disposition?.description ?? "",
            resolution_notes: disposition?.resolution_notes ?? "",
            resolution_performed_by: disposition?.resolution_performed_by ?? null,
            // Containment (who RECORDED it is stamped by the server; the form sets
            // who did it, if someone else)
            containment_action: disposition?.containment_action ?? "",
            containment_completed: false,
            containment_performed_by: disposition?.containment_performed_by ?? null,
            // Customer approval
            requires_customer_approval: disposition?.requires_customer_approval ?? false,
            customer_approval_received: disposition?.customer_approval_received ?? false,
            customer_approval_reference: disposition?.customer_approval_reference ?? "",
            customer_approval_date: disposition?.customer_approval_date,
            // Relationships
            quality_reports: disposition?.quality_reports ?? []
        },
    })

    const {control, handleSubmit, formState: {isSubmitting}, watch} = form;
    const watchDispositionType = watch("disposition_type");
    const watchSeverity = watch("severity");
    const showCustomerApproval = watchDispositionType === "USE_AS_IS" || watchDispositionType === "REPAIR";

    // Auto-expand containment section when severity is critical
    React.useEffect(() => {
        if (watchSeverity === "CRITICAL") {
            setContainmentOpen(true);
        }
    }, [watchSeverity]);

    if (employeesLoading) {
        return (<div className="flex h-full items-center justify-center p-6">
                <Loader2 className="h-4 w-4 animate-spin mr-2"/>
                <p className="text-sm text-muted-foreground">Loading form data...</p>
            </div>);
    }

    const onSubmit = async (values: FormValues) => {
        // Client-side warning if trying to close with pending annotations
        if (values.current_state === "CLOSED" && disposition?.annotation_status?.has_pending) {
            toast.error("Cannot close disposition: 3D annotations are required. Please complete annotations first.");
            return;
        }

        try {
            if (disposition?.id) {
                await api.api_QuarantineDispositions_partial_update(values, {
                    params: { id: disposition.id },
                    headers: {"X-CSRFToken": getCookie("csrftoken") ?? ""},
                });
                toast.success("Disposition Updated");
            } else {
                await api.api_QuarantineDispositions_create(values, {
                    headers: {"X-CSRFToken": getCookie("csrftoken") ?? ""},
                });
                toast.success("Disposition Created");
            }
            onClose?.();
        } catch (err: any) {
            console.error("API Error:", err);
            // Try to extract error message from response
            const errorMessage = err?.response?.data?.detail
                || err?.response?.data?.message
                || err?.message
                || (disposition?.id ? "Failed to update Disposition" : "Failed to create Disposition");
            toast.error(errorMessage);
        }
    };




    return (
        <Form {...form}>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col h-full">
                {disposition?.disposition_number && (
                    <div className="px-6 pt-6 pb-2">
                        <h3 className="text-lg font-semibold">Disposition #{disposition.disposition_number}</h3>
                    </div>
                )}

                {/* Annotation status alert */}
                {disposition?.annotation_status?.has_pending && (
                    <div className="px-6 pt-2">
                        <Alert variant="destructive">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>3D Annotations Required</AlertTitle>
                            <AlertDescription className="space-y-2">
                                <p>
                                    {disposition.annotation_status.pending_count} quality report(s) require 3D annotations
                                    before this disposition can be closed.
                                </p>
                                <Link to="/annotator">
                                    <Button variant="outline" size="sm" className="gap-2">
                                        <ExternalLink className="h-4 w-4" />
                                        Go to Annotator
                                    </Button>
                                </Link>
                            </AlertDescription>
                        </Alert>
                    </div>
                )}

                {/* Completion blockers (other than annotations) */}
                {disposition?.completion_blockers?.length > 0 && !disposition?.annotation_status?.has_pending && (
                    <div className="px-6 pt-2">
                        <Alert>
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>Cannot Close Disposition</AlertTitle>
                            <AlertDescription>
                                <ul className="list-disc list-inside">
                                    {disposition.completion_blockers.map((blocker: string, i: number) => (
                                        <li key={i}>{blocker}</li>
                                    ))}
                                </ul>
                            </AlertDescription>
                        </Alert>
                    </div>
                )}

                <div className="flex-1 space-y-6 p-6 overflow-y-auto">

            <FormField
                control={control}
                name="current_state"
                render={({field}) => (<FormItem>
                        <FormLabel required={required.current_state}>Current State</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select current state"/>
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                {schemas.CurrentStateEnum.options.map((state) => (
                                    <SelectItem key={state} value={state}>
                                        {currentStateLabels[state] ?? state}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <FormDescription>State of the disposition as it currently is</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
            />

            <FormField
                control={control}
                name="disposition_type"
                render={({field}) => (<FormItem>
                        <FormLabel required={required.disposition_type}>Disposition Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value as string | undefined}>
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select disposition type"/>
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                {schemas.DispositionTypeEnum.options.map((type) => (
                                    <SelectItem key={type} value={type}>
                                        {dispositionTypeLabels[type] ?? type}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <FormDescription>The type of resolution for this disposition</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
            />

            <FormField
                control={control}
                name="severity"
                render={({field}) => (<FormItem>
                        <FormLabel required={required.severity}>Severity</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select severity"/>
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                {schemas.SeverityEnum.options.map((sev) => (
                                    <SelectItem key={sev} value={sev}>
                                        {severityLabels[sev] ?? sev}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <FormDescription>Severity classification of the nonconformance</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
            />

            <FormField
                control={control}
                name="assigned_to"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Assigned To</FormLabel>
                        <FormControl>
                            <Combobox
                                value={field.value == null ? null : String(field.value)}
                                onChange={(v) => v && field.onChange(Number(v))}
                                options={employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` }))}
                                placeholder="Select employee"
                                searchPlaceholder="Search..."
                                emptyText="No employees found."
                            />
                        </FormControl>
                        <FormDescription>Who this resolution is assigned to</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            <FormField
                control={control}
                name="description"
                render={({field}) => (
                    <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                            <Textarea
                                placeholder="Add description for this disposition..."
                                className="resize-none"
                                {...field}
                            />
                        </FormControl>
                        <FormDescription>
                            Description for this disposition, not related to the resolution itself
                        </FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            {/* Containment Section - Collapsible */}
            <Collapsible open={containmentOpen} onOpenChange={setContainmentOpen}>
                <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-between p-2 h-auto">
                        <span className="font-medium">Containment Action</span>
                        <ChevronDown className={cn("h-4 w-4 transition-transform", containmentOpen && "rotate-180")} />
                    </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 pt-2">
                    <FormField
                        control={control}
                        name="containment_action"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Containment Action Taken</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe immediate containment action (e.g., segregated parts, stopped production)..."
                                        className="resize-none"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Immediate action taken to prevent defect escape (IATF 16949 requirement)
                                </FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />
                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            control={control}
                            name="containment_performed_by"
                            render={({field}) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Performed by <span className="text-muted-foreground">(if not you)</span></FormLabel>
                                    <FormControl>
                                        <Combobox
                                            value={field.value == null ? null : String(field.value)}
                                            onChange={(v) => field.onChange(v ? Number(v) : null)}
                                            options={employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` }))}
                                            placeholder="Select employee"
                                            searchPlaceholder="Search..."
                                            emptyText="No employees found."
                                            clearLabel="Nobody else"
                                        />
                                    </FormControl>
                                    <FormMessage/>
                                </FormItem>
                            )}
                        />
                        {disposition?.containment_completed_at ? (
                            <div className="flex flex-col justify-end text-sm text-muted-foreground">
                                Containment recorded by {disposition.containment_completed_by_name ?? "—"} on{" "}
                                {format(new Date(disposition.containment_completed_at), "PPP")}
                            </div>
                        ) : (
                            <FormField
                                control={form.control}
                                name="containment_completed"
                                render={({field}) => (
                                    <FormItem className="flex flex-row items-end space-x-3 space-y-0 pb-2">
                                        <FormControl>
                                            <Checkbox checked={field.value ?? false} onCheckedChange={field.onChange}/>
                                        </FormControl>
                                        <div className="space-y-1 leading-none">
                                            <FormLabel>Containment complete</FormLabel>
                                            <FormDescription>Records you, and now, as having recorded it.</FormDescription>
                                        </div>
                                    </FormItem>
                                )}
                            />
                        )}
                    </div>
                    {/* Document upload for containment evidence - only for existing dispositions */}
                    {disposition?.id && dispositionContentType && (
                        <div className="pt-2 border-t">
                            <DocumentUploader
                                objectId={disposition.id}
                                contentType={String(dispositionContentType.id)}
                                documentTypeCode="CONT_EVD"
                                title="Attach Containment Evidence"
                                compact
                            />
                        </div>
                    )}
                </CollapsibleContent>
            </Collapsible>

            {/* Customer Approval Section - Shown for USE_AS_IS or REPAIR */}
            {showCustomerApproval && (
                <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                    <h4 className="font-medium text-sm">Customer Approval Required</h4>
                    <p className="text-sm text-muted-foreground">
                        {watchDispositionType === "REPAIR" ? "Repair" : "Use As Is"} dispositions may require customer approval.
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            control={control}
                            name="requires_customer_approval"
                            render={({field}) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                    <FormControl>
                                        <Checkbox checked={field.value} onCheckedChange={field.onChange}/>
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Requires Approval</FormLabel>
                                    </div>
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={control}
                            name="customer_approval_received"
                            render={({field}) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                    <FormControl>
                                        <Checkbox checked={field.value} onCheckedChange={field.onChange}/>
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Approval Received</FormLabel>
                                    </div>
                                </FormItem>
                            )}
                        />
                    </div>
                    <FormField
                        control={control}
                        name="customer_approval_reference"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Approval Reference</FormLabel>
                                <FormControl>
                                    <Input placeholder="PO#, email reference, or approval document number" {...field}/>
                                </FormControl>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="customer_approval_date"
                        render={({field}) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Approval Date</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button variant="outline" className={cn("w-[240px] pl-3 text-left font-normal", !field.value && "text-muted-foreground")}>
                                                {field.value ? format(new Date(field.value), "PPP") : <span>Pick a date</span>}
                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar mode="single" selected={field.value ? new Date(field.value) : undefined} onSelect={(date) => field.onChange(date?.toISOString())} initialFocus/>
                                    </PopoverContent>
                                </Popover>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />
                    {/* Document upload for customer approval evidence - only for existing dispositions */}
                    {disposition?.id && dispositionContentType && (
                        <div className="pt-2 border-t">
                            <DocumentUploader
                                objectId={disposition.id}
                                contentType={String(dispositionContentType.id)}
                                documentTypeCode="CUST_APPR"
                                title="Attach Approval Evidence"
                                compact
                            />
                        </div>
                    )}
                </div>
            )}

            <FormField
                control={control}
                name="resolution_notes"
                render={({field}) => (
                    <FormItem>
                        <FormLabel>Resolution Notes</FormLabel>
                        <FormControl>
                            <Textarea
                                placeholder="Add resolution notes..."
                                className="resize-none"
                                {...field}
                            />
                        </FormControl>
                        <FormDescription>Notes for this particular disposition's resolution</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
            <FormField
                control={control}
                name="resolution_performed_by"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Resolution performed by <span className="text-muted-foreground">(if not you)</span></FormLabel>
                        <FormControl>
                            <Combobox
                                value={field.value == null ? null : String(field.value)}
                                onChange={(v) => field.onChange(v ? Number(v) : null)}
                                options={employees.map((emp) => ({ value: String(emp.id), label: `${emp.first_name} ${emp.last_name}` }))}
                                placeholder="Select employee"
                                searchPlaceholder="Search..."
                                emptyText="No employees found."
                                clearLabel="Nobody else"
                            />
                        </FormControl>
                        <FormDescription>
                            {disposition?.resolution_completed_at
                                ? `Resolution recorded on ${format(new Date(disposition.resolution_completed_at), "PPP")}.`
                                : "Closing the disposition records who resolved it, and when."}
                        </FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
            <FormField
                control={control}
                name="part"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Related Part</FormLabel>
                        <FormControl>
                            <Combobox
                                value={field.value || null}
                                onChange={(v) => v && field.onChange(v)}
                                options={parts.map((p) => ({ value: p.id, label: p.ERP_id, ...(p.part_type_name ? { description: p.part_type_name } : {}) }))}
                                onSearch={setPartSearch}
                                selectedLabel={field.value ? `Part #${field.value}` : undefined}
                                placeholder="Select part"
                                searchPlaceholder="Search parts..."
                                emptyText="No parts found."
                            />
                        </FormControl>
                        <FormDescription>The part that this disposition is related to</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
            <FormField
                control={control}
                name="quality_reports"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Quality Reports</FormLabel>
                        <MultiPicker
                            label="Quality reports"
                            hideLabel
                            items={qualityReports.map((qr) => ({
                                id: qr.id,
                                label: `Report #${qr.id}`,
                                description: [
                                    `Part #${qr.part}`,
                                    qr.created_at ? format(new Date(qr.created_at), "MMM dd, yyyy") : null,
                                    qr.status,
                                ].filter(Boolean).join(" · "),
                            }))}
                            selected={field.value ?? []}
                            onChange={field.onChange}
                            onSearch={setQualityReportSearch}
                            placeholder="Select quality reports"
                            searchPlaceholder="Search quality reports..."
                            emptyHint="No quality reports found."
                        />
                        <FormMessage/>
                    </FormItem>
                )}
            />
                </div>

                <div className="flex justify-end space-x-2 p-6 border-t bg-background">
                    {onClose && (
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                    )}
                    <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="min-w-[120px]"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            "Submit Disposition"
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    )
}