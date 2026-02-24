import * as React from "react";
import {Button} from "@/components/ui/button";
import {toast} from "sonner";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {api, schemas, type PaginatedUserSelectList} from "@/lib/api/generated";
import {isFieldRequired} from "@/lib/zod-config";
import {useInfiniteQuery} from "@tanstack/react-query";
import {useQualityReports} from "@/hooks/useQualityReports";
import {useRetrieveParts} from "@/hooks/useRetrieveParts";
import {cn, getCookie} from "@/lib/utils";
import {Popover, PopoverContent, PopoverTrigger,} from "@/components/ui/popover";
import {Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,} from "@/components/ui/command";
import {Textarea} from "@/components/ui/textarea";
import {Input} from "@/components/ui/input";
import {Checkbox} from "@/components/ui/checkbox";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Collapsible, CollapsibleContent, CollapsibleTrigger} from "@/components/ui/collapsible";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,} from "@/components/ui/form";
import {Calendar as CalendarIcon, Check, ChevronsUpDown, ChevronDown, Loader2, AlertTriangle, ExternalLink} from "lucide-react";
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
    resolution_completed_by: true,
    resolution_completed_at: true,
    containment_action: true,
    containment_completed_at: true,
    containment_completed_by: true,
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

export default function PartDispositionForm({part, disposition, onClose}: { part: any; disposition?: any; onClose?: () => void }) {
    const [assignedToPopoverOpen, setAssignedToPopoverOpen] = React.useState(false);
    const [completedByPopoverOpen, setCompletedByPopoverOpen] = React.useState(false);
    const [containmentByPopoverOpen, setContainmentByPopoverOpen] = React.useState(false);
    const [partPopoverOpen, setPartPopoverOpen] = React.useState(false);
    const [qualityReportsPopoverOpen, setQualityReportsPopoverOpen] = React.useState(false);
    const [assignedToSearch, setAssignedToSearch] = React.useState("");
    const [completedBySearch, setCompletedBySearch] = React.useState("");
    const [containmentBySearch, setContainmentBySearch] = React.useState("");
    const [partSearch, setPartSearch] = React.useState("");
    const [qualityReportSearch, setQualityReportSearch] = React.useState("");
    // Collapsible state for containment section - expanded by default for CRITICAL
    const [containmentOpen, setContainmentOpen] = React.useState(disposition?.severity === "CRITICAL");

    const {data: employeePages, isLoading: employeesLoading} = useInfiniteQuery<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({pageParam = 0}) => api.api_Employees_Options_list({queries: {offset: pageParam}}),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

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
            resolution_completed_by: disposition?.resolution_completed_by,
            resolution_completed_at: disposition?.resolution_completed_at ?? new Date().toISOString(),
            // Containment
            containment_action: disposition?.containment_action ?? "",
            containment_completed_at: disposition?.containment_completed_at,
            containment_completed_by: disposition?.containment_completed_by,
            // Customer approval
            requires_customer_approval: disposition?.requires_customer_approval ?? false,
            customer_approval_received: disposition?.customer_approval_received ?? false,
            customer_approval_reference: disposition?.customer_approval_reference ?? "",
            customer_approval_date: disposition?.customer_approval_date,
            // Relationships
            quality_reports: disposition?.quality_reports ?? []
        },
    })

    const {control, handleSubmit, formState: {isSubmitting, errors}, watch} = form;
    const watchDispositionType = watch("disposition_type");
    const watchSeverity = watch("severity");
    const showCustomerApproval = watchDispositionType === "USE_AS_IS" || watchDispositionType === "REPAIR";

    // Auto-expand containment section when severity is CRITICAL
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

    const filteredAssignedTo = employees.filter((emp) => `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(assignedToSearch.toLowerCase()));

    const filteredCompletedBy = employees.filter((emp) => `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(completedBySearch.toLowerCase()));

    const filteredContainmentBy = employees.filter((emp) => `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(containmentBySearch.toLowerCase()));

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
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                        <Popover open={assignedToPopoverOpen} onOpenChange={setAssignedToPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={assignedToPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? employees.find((emp) => emp.id === field.value)?.first_name + " " + employees.find((emp) => emp.id === field.value)?.last_name
                                            : "Select employee"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search employees..."
                                        value={assignedToSearch}
                                        onValueChange={setAssignedToSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No employees found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredAssignedTo.map((employee) => (
                                                <CommandItem
                                                    key={employee.id}
                                                    onSelect={() => {
                                                        field.onChange(employee.id);
                                                        setAssignedToPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === employee.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {employee.first_name} {employee.last_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
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
                            name="containment_completed_by"
                            render={({field}) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Completed By</FormLabel>
                                    <Popover open={containmentByPopoverOpen} onOpenChange={setContainmentByPopoverOpen}>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button variant="outline" role="combobox" className="w-full justify-between">
                                                    {field.value
                                                        ? employees.find((emp) => emp.id === field.value)?.first_name + " " + employees.find((emp) => emp.id === field.value)?.last_name
                                                        : "Select employee"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0">
                                            <Command>
                                                <CommandInput placeholder="Search..." value={containmentBySearch} onValueChange={setContainmentBySearch}/>
                                                <CommandList>
                                                    <CommandEmpty>No employees found.</CommandEmpty>
                                                    <CommandGroup className="max-h-64 overflow-auto">
                                                        {filteredContainmentBy.map((employee) => (
                                                            <CommandItem key={employee.id} onSelect={() => { field.onChange(employee.id); setContainmentByPopoverOpen(false); }}>
                                                                <Check className={cn("mr-2 h-4 w-4", field.value === employee.id ? "opacity-100" : "opacity-0")}/>
                                                                {employee.first_name} {employee.last_name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormMessage/>
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="containment_completed_at"
                            render={({field}) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Completed At</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button variant="outline" className={cn("w-full pl-3 text-left font-normal", !field.value && "text-muted-foreground")}>
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
                name="resolution_completed_by"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Resolution Completed By</FormLabel>
                        <Popover open={completedByPopoverOpen} onOpenChange={setCompletedByPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={completedByPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? employees.find((emp) => emp.id === field.value)?.first_name + " " + employees.find((emp) => emp.id === field.value)?.last_name
                                            : "Select employee"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search employees..."
                                        value={completedBySearch}
                                        onValueChange={setCompletedBySearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No employees found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredCompletedBy.map((employee) => (
                                                <CommandItem
                                                    key={employee.id}
                                                    onSelect={() => {
                                                        field.onChange(employee.id);
                                                        setCompletedByPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === employee.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {employee.first_name} {employee.last_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        <FormDescription>
                            Who completed the resolution or may verify that the resolution has been completed
                        </FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            <FormField
                control={form.control}
                name="resolution_completed_at"
                render={({field}) => (<FormItem className="flex flex-col">
                    <FormLabel>Resolution Completion Date</FormLabel>
                    <Popover>
                        <PopoverTrigger asChild>
                            <FormControl>
                                <Button
                                    variant={"outline"}
                                    className={cn("w-[240px] pl-3 text-left font-normal", !field.value && "text-muted-foreground")}
                                >
                                    {field.value ? (format(field.value, "PPP")) : (<span>Pick a date</span>)}
                                    <CalendarIcon className="ml-auto h-4 w-4 opacity-50"/>
                                </Button>
                            </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                            <Calendar
                                mode="single"
                                selected={field.value}
                                onSelect={field.onChange}
                                initialFocus
                            />
                        </PopoverContent>
                    </Popover>
                    <FormDescription>The date on which that this resolution was completed</FormDescription>
                    <FormMessage/>
                </FormItem>)}
            />
            <FormField
                control={control}
                name="part"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Related Part</FormLabel>
                        <Popover open={partPopoverOpen} onOpenChange={setPartPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={partPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? parts.find((p) => p.id === field.value)?.ERP_id || `Part #${field.value}`
                                            : "Select part"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search parts..."
                                        value={partSearch}
                                        onValueChange={setPartSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No parts found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {parts.map((p) => (
                                                <CommandItem
                                                    key={p.id}
                                                    onSelect={() => {
                                                        field.onChange(p.id);
                                                        setPartPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === p.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {p.ERP_id} - {p.part_type_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
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
                        <Popover open={qualityReportsPopoverOpen} onOpenChange={setQualityReportsPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={qualityReportsPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value && field.value.length > 0
                                            ? `${field.value.length} report${field.value.length > 1 ? 's' : ''} selected`
                                            : "Select quality reports"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search quality reports..."
                                        value={qualityReportSearch}
                                        onValueChange={setQualityReportSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No quality reports found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {qualityReports.map((qr) => (
                                                <CommandItem
                                                    key={qr.id}
                                                    onSelect={() => {
                                                        const currentValue = field.value || [];
                                                        const newValue = currentValue.includes(qr.id)
                                                            ? currentValue.filter((id) => id !== qr.id)
                                                            : [...currentValue, qr.id];
                                                        field.onChange(newValue);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value?.includes(qr.id) ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    Report #{qr.id} - Part #{qr.part} - {qr.created_at ? format(new Date(qr.created_at), 'MMM dd, yyyy') : 'No date'}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        {field.value && field.value.length > 0 && (
                            <div className="mt-2 space-y-1">
                                <p className="text-sm font-medium text-muted-foreground">Selected Reports:</p>
                                <ul className="text-sm text-muted-foreground space-y-1">
                                    {field.value.map(id => {
                                        const report = qualityReports.find(qr => qr.id === id);
                                        if (!report) return <li key={id}>#{id}</li>;
                                        const dateStr = report.created_at ? format(new Date(report.created_at), 'MMM dd, yyyy') : 'No date';
                                        return (
                                            <li key={id} className="flex items-center gap-2">
                                                <span className="font-mono">#{id}</span>
                                                <span>-</span>
                                                <span>Part #{report.part}</span>
                                                <span>-</span>
                                                <span>{dateStr}</span>
                                                <span className={`px-2 py-0.5 rounded text-xs ${
                                                    report.status === 'PASS' ? 'bg-green-100 text-green-800' :
                                                    report.status === 'FAIL' ? 'bg-red-100 text-red-800' :
                                                    'bg-yellow-100 text-yellow-800'
                                                }`}>
                                                    {report.status}
                                                </span>
                                            </li>
                                        );
                                    })}
                                </ul>
                            </div>
                        )}
                        <FormDescription>Quality reports that this disposition is related to</FormDescription>
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