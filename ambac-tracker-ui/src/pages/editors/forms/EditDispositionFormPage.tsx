"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { format } from "date-fns"
import { useParams, useSearch, useNavigate, Link } from "@tanstack/react-router"
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query"

import { cn, getCookie } from "@/lib/utils"
import { api, type PaginatedUserSelectList } from "@/lib/api/generated"
import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Calendar } from "@/components/ui/calendar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import {
    ArrowLeft,
    Calendar as CalendarIcon,
    Check,
    ChevronsUpDown,
    ChevronDown,
    Loader2,
    AlertTriangle,
    ExternalLink,
    CheckCircle,
    FileText,
} from "lucide-react"

import { useRetrieveDisposition } from "@/hooks/useRetrieveDisposition"
import { useRetrievePart } from "@/hooks/useRetrievePart"
import { useRetrieveParts } from "@/hooks/useRetrieveParts"
import { useQualityReports } from "@/hooks/useQualityReports"
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes"
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader"
import { schemas } from "@/lib/api/generated"
import { isFieldRequired } from "@/lib/zod-config"

// Use generated schema - error messages handled by global error map
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
    part: true,
    quality_reports: true,
})

type FormValues = z.infer<typeof formSchema>

// Pre-compute required fields for labels
const required = {
    current_state: isFieldRequired(formSchema.shape.current_state),
    disposition_type: isFieldRequired(formSchema.shape.disposition_type),
    severity: isFieldRequired(formSchema.shape.severity),
    assigned_to: isFieldRequired(formSchema.shape.assigned_to),
    description: isFieldRequired(formSchema.shape.description),
    resolution_notes: isFieldRequired(formSchema.shape.resolution_notes),
    part: isFieldRequired(formSchema.shape.part),
    quality_reports: isFieldRequired(formSchema.shape.quality_reports),
}

// Label maps for enums with custom display text
const currentStateLabels: Record<string, string> = {
    OPEN: "Open",
    IN_PROGRESS: "In Progress",
    CLOSED: "Closed",
}

const dispositionTypeLabels: Record<string, string> = {
    REWORK: "Rework",
    REPAIR: "Repair (AS9100)",
    SCRAP: "Scrap",
    USE_AS_IS: "Use As Is",
    RETURN_TO_SUPPLIER: "Return to Supplier",
}

const severityLabels: Record<string, string> = {
    CRITICAL: "Critical - Safety/Regulatory Impact",
    MAJOR: "Major - Functional Impact",
    MINOR: "Minor - Cosmetic Only",
}

// Search params for create mode
type DispositionSearchParams = {
    partId?: string
    qualityReportId?: string
}

export default function EditDispositionFormPage() {
    const params = useParams({ strict: false })
    const searchParams = useSearch({ strict: false }) as DispositionSearchParams
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const mode = params.id ? "edit" : "create"
    const dispositionId = params.id

    // Parse URL search params for create mode
    const initialPartId = searchParams.partId
    const initialQualityReportId = searchParams.qualityReportId

    // Fetch disposition data in edit mode
    const { data: disposition, isLoading: dispositionLoading } = useRetrieveDisposition(dispositionId)

    // Determine part ID (from disposition in edit mode, from URL in create mode)
    const partId = mode === "edit" ? disposition?.part : initialPartId

    // Fetch part data for context panel
    const { data: part } = useRetrievePart(
        { params: { id: partId! } },
        { enabled: !!partId }
    )

    // Fetch employees for dropdowns
    const { data: employeePages, isLoading: employeesLoading } = useInfiniteQuery<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    })
    const employees = employeePages?.pages.flatMap((p) => p.results) ?? []

    // Fetch content types for document upload
    const { data: contentTypes } = useRetrieveContentTypes({})
    const dispositionContentType = contentTypes?.find(
        (ct: any) => ct.model === "quarantinedisposition" && ct.app_label === "Tracker"
    )

    // Fetch parts and quality reports for form dropdowns
    const [partSearch, setPartSearch] = useState("")
    const [qualityReportSearch, setQualityReportSearch] = useState("")
    const { data: partsData } = useRetrieveParts({ limit: 100, search: partSearch })
    const { data: qualityReportsData } = useQualityReports({ limit: 100, search: qualityReportSearch })
    const parts = partsData?.results ?? []
    const qualityReports = qualityReportsData?.results ?? []

    // Popover states
    const [assignedToPopoverOpen, setAssignedToPopoverOpen] = useState(false)
    const [completedByPopoverOpen, setCompletedByPopoverOpen] = useState(false)
    const [containmentByPopoverOpen, setContainmentByPopoverOpen] = useState(false)
    const [partPopoverOpen, setPartPopoverOpen] = useState(false)
    const [qualityReportsPopoverOpen, setQualityReportsPopoverOpen] = useState(false)

    // Search states for employee filtering
    const [assignedToSearch, setAssignedToSearch] = useState("")
    const [completedBySearch, setCompletedBySearch] = useState("")
    const [containmentBySearch, setContainmentBySearch] = useState("")

    // Collapsible states
    const [containmentOpen, setContainmentOpen] = useState(false)

    // Form setup
    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            part: initialPartId ?? null,
            current_state: "OPEN",
            disposition_type: undefined,
            severity: "MAJOR",
            assigned_to: undefined,
            description: "",
            resolution_notes: "",
            resolution_completed_by: undefined,
            resolution_completed_at: new Date().toISOString(),
            containment_action: "",
            containment_completed_at: undefined,
            containment_completed_by: undefined,
            requires_customer_approval: false,
            customer_approval_received: false,
            customer_approval_reference: "",
            customer_approval_date: undefined,
            quality_reports: initialQualityReportId ? [initialQualityReportId] : [],
        },
    })

    // Reset form when disposition data loads in edit mode
    useEffect(() => {
        if (mode === "edit" && disposition) {
            form.reset({
                part: disposition.part ?? null,
                current_state: disposition.current_state ?? "OPEN",
                disposition_type: disposition.disposition_type,
                severity: disposition.severity ?? "MAJOR",
                assigned_to: disposition.assigned_to,
                description: disposition.description ?? "",
                resolution_notes: disposition.resolution_notes ?? "",
                resolution_completed_by: disposition.resolution_completed_by,
                resolution_completed_at: disposition.resolution_completed_at ?? new Date().toISOString(),
                containment_action: disposition.containment_action ?? "",
                containment_completed_at: disposition.containment_completed_at,
                containment_completed_by: disposition.containment_completed_by,
                requires_customer_approval: disposition.requires_customer_approval ?? false,
                customer_approval_received: disposition.customer_approval_received ?? false,
                customer_approval_reference: disposition.customer_approval_reference ?? "",
                customer_approval_date: disposition.customer_approval_date,
                quality_reports: disposition.quality_reports ?? [],
            })
            // Expand containment section for CRITICAL severity
            if (disposition.severity === "CRITICAL") {
                setContainmentOpen(true)
            }
        }
    }, [mode, disposition, form])

    const { control, handleSubmit, formState: { isSubmitting, _errors }, watch } = form
    const watchDispositionType = watch("disposition_type")
    const watchSeverity = watch("severity")
    const showCustomerApproval = watchDispositionType === "USE_AS_IS" || watchDispositionType === "REPAIR"

    // Auto-expand containment section when severity changes to CRITICAL
    useEffect(() => {
        if (watchSeverity === "CRITICAL") {
            setContainmentOpen(true)
        }
    }, [watchSeverity])

    // Filtered employee lists
    const filteredAssignedTo = employees.filter((emp) =>
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(assignedToSearch.toLowerCase())
    )
    const filteredCompletedBy = employees.filter((emp) =>
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(completedBySearch.toLowerCase())
    )
    const filteredContainmentBy = employees.filter((emp) =>
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(containmentBySearch.toLowerCase())
    )

    // Form submission
    const onSubmit = async (values: FormValues) => {
        // Client-side validation for closing with pending annotations
        if (mode === "edit" && values.current_state === "CLOSED" && disposition?.annotation_status?.has_pending) {
            toast.error("Cannot close disposition: 3D annotations are required. Please complete annotations first.")
            return
        }

        try {
            if (mode === "edit" && dispositionId) {
                await api.api_QuarantineDispositions_partial_update(values, {
                    params: { id: dispositionId },
                    headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                })
                toast.success("Disposition updated")
                queryClient.invalidateQueries({ queryKey: ["disposition", dispositionId] })
            } else {
                const result = await api.api_QuarantineDispositions_create(values, {
                    headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                })
                toast.success("Disposition created")
                // Navigate to edit page for the new disposition
                navigate({ to: "/dispositions/edit/$id", params: { id: String(result.id) } })
            }
        } catch (err: any) {
            console.error("API Error:", err)
            const errorMessage = err?.response?.data?.detail
                || err?.response?.data?.message
                || err?.message
                || (mode === "edit" ? "Failed to update disposition" : "Failed to create disposition")
            toast.error(errorMessage)
        }
    }

    // Loading state
    if (mode === "edit" && (dispositionLoading || employeesLoading)) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                <p className="text-sm text-muted-foreground">Loading disposition...</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-14 items-center gap-4">
                    <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/production/dispositions" })}>
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back
                    </Button>
                    <Separator orientation="vertical" className="h-6" />
                    <div className="flex items-center gap-2">
                        <h1 className="text-lg font-semibold">
                            {mode === "edit"
                                ? `Disposition #${disposition?.disposition_number ?? dispositionId}`
                                : "New Disposition"
                            }
                        </h1>
                        {mode === "edit" && disposition && (
                            <>
                                <Badge variant={
                                    disposition.current_state === "CLOSED" ? "default" :
                                    disposition.current_state === "IN_PROGRESS" ? "secondary" : "outline"
                                }>
                                    {disposition.current_state?.replace("_", " ")}
                                </Badge>
                                <Badge variant={
                                    disposition.severity === "CRITICAL" ? "destructive" :
                                    disposition.severity === "MAJOR" ? "secondary" : "outline"
                                }>
                                    {disposition.severity}
                                </Badge>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content - Split Layout */}
            <div className="container py-6">
                <div className="grid gap-6 lg:grid-cols-3">
                    {/* Form Section (2/3 width) */}
                    <div className="lg:col-span-2">
                        <Card>
                            <CardHeader>
                                <CardTitle>Disposition Details</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Form {...form}>
                                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                                        {/* Annotation status alert */}
                                        {mode === "edit" && disposition?.annotation_status?.has_pending && (
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
                                        )}

                                        {/* State & Type Row */}
                                        <div className="grid gap-4 md:grid-cols-2">
                                            <FormField
                                                control={control}
                                                name="current_state"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel required={required.current_state}>Current State</FormLabel>
                                                        <Select onValueChange={field.onChange} value={field.value}>
                                                            <FormControl>
                                                                <SelectTrigger>
                                                                    <SelectValue placeholder="Select state" />
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
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />

                                            <FormField
                                                control={control}
                                                name="disposition_type"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel required={required.disposition_type}>Disposition Type</FormLabel>
                                                        <Select onValueChange={field.onChange} value={field.value}>
                                                            <FormControl>
                                                                <SelectTrigger>
                                                                    <SelectValue placeholder="Select type" />
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
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>

                                        {/* Severity */}
                                        <FormField
                                            control={control}
                                            name="severity"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel required={required.severity}>Severity</FormLabel>
                                                    <Select onValueChange={field.onChange} value={field.value}>
                                                        <FormControl>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder="Select severity" />
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
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Assigned To */}
                                        <FormField
                                            control={control}
                                            name="assigned_to"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel required={required.assigned_to}>Assigned To</FormLabel>
                                                    <Popover open={assignedToPopoverOpen} onOpenChange={setAssignedToPopoverOpen}>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button variant="outline" role="combobox" className="w-full justify-between">
                                                                    {field.value
                                                                        ? `${employees.find((emp) => emp.id === field.value)?.first_name} ${employees.find((emp) => emp.id === field.value)?.last_name}`
                                                                        : "Select employee"
                                                                    }
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-full p-0">
                                                            <Command>
                                                                <CommandInput placeholder="Search..." value={assignedToSearch} onValueChange={setAssignedToSearch} />
                                                                <CommandList>
                                                                    <CommandEmpty>No employees found.</CommandEmpty>
                                                                    <CommandGroup className="max-h-64 overflow-auto">
                                                                        {filteredAssignedTo.map((emp) => (
                                                                            <CommandItem
                                                                                key={emp.id}
                                                                                onSelect={() => {
                                                                                    field.onChange(emp.id)
                                                                                    setAssignedToPopoverOpen(false)
                                                                                }}
                                                                            >
                                                                                <Check className={cn("mr-2 h-4 w-4", field.value === emp.id ? "opacity-100" : "opacity-0")} />
                                                                                {emp.first_name} {emp.last_name}
                                                                            </CommandItem>
                                                                        ))}
                                                                    </CommandGroup>
                                                                </CommandList>
                                                            </Command>
                                                        </PopoverContent>
                                                    </Popover>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Description */}
                                        <FormField
                                            control={control}
                                            name="description"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel required={required.description}>Description</FormLabel>
                                                    <FormControl>
                                                        <Textarea placeholder="Describe the nonconformance..." className="resize-none" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Containment Section */}
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
                                                    render={({ field }) => (
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
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                                <div className="grid grid-cols-2 gap-4">
                                                    <FormField
                                                        control={control}
                                                        name="containment_completed_by"
                                                        render={({ field }) => (
                                                            <FormItem className="flex flex-col">
                                                                <FormLabel>Completed By</FormLabel>
                                                                <Popover open={containmentByPopoverOpen} onOpenChange={setContainmentByPopoverOpen}>
                                                                    <PopoverTrigger asChild>
                                                                        <FormControl>
                                                                            <Button variant="outline" role="combobox" className="w-full justify-between">
                                                                                {field.value
                                                                                    ? `${employees.find((emp) => emp.id === field.value)?.first_name} ${employees.find((emp) => emp.id === field.value)?.last_name}`
                                                                                    : "Select employee"
                                                                                }
                                                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                            </Button>
                                                                        </FormControl>
                                                                    </PopoverTrigger>
                                                                    <PopoverContent className="w-full p-0">
                                                                        <Command>
                                                                            <CommandInput placeholder="Search..." value={containmentBySearch} onValueChange={setContainmentBySearch} />
                                                                            <CommandList>
                                                                                <CommandEmpty>No employees found.</CommandEmpty>
                                                                                <CommandGroup className="max-h-64 overflow-auto">
                                                                                    {filteredContainmentBy.map((emp) => (
                                                                                        <CommandItem
                                                                                            key={emp.id}
                                                                                            onSelect={() => {
                                                                                                field.onChange(emp.id)
                                                                                                setContainmentByPopoverOpen(false)
                                                                                            }}
                                                                                        >
                                                                                            <Check className={cn("mr-2 h-4 w-4", field.value === emp.id ? "opacity-100" : "opacity-0")} />
                                                                                            {emp.first_name} {emp.last_name}
                                                                                        </CommandItem>
                                                                                    ))}
                                                                                </CommandGroup>
                                                                            </CommandList>
                                                                        </Command>
                                                                    </PopoverContent>
                                                                </Popover>
                                                                <FormMessage />
                                                            </FormItem>
                                                        )}
                                                    />
                                                    <FormField
                                                        control={control}
                                                        name="containment_completed_at"
                                                        render={({ field }) => (
                                                            <FormItem className="flex flex-col">
                                                                <FormLabel>Completed At</FormLabel>
                                                                <Popover>
                                                                    <PopoverTrigger asChild>
                                                                        <FormControl>
                                                                            <Button variant="outline" className={cn("w-full pl-3 text-left font-normal", !field.value && "text-muted-foreground")}>
                                                                                {field.value ? format(new Date(field.value), "PPP") : <span>Pick a date</span>}
                                                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                                            </Button>
                                                                        </FormControl>
                                                                    </PopoverTrigger>
                                                                    <PopoverContent className="w-auto p-0" align="start">
                                                                        <Calendar
                                                                            mode="single"
                                                                            selected={field.value ? new Date(field.value) : undefined}
                                                                            onSelect={(date) => field.onChange(date?.toISOString())}
                                                                            initialFocus
                                                                        />
                                                                    </PopoverContent>
                                                                </Popover>
                                                                <FormMessage />
                                                            </FormItem>
                                                        )}
                                                    />
                                                </div>
                                                {/* Document upload for containment evidence */}
                                                {mode === "edit" && dispositionId && dispositionContentType && (
                                                    <div className="pt-2 border-t">
                                                        <DocumentUploader
                                                            objectId={dispositionId}
                                                            contentType={String(dispositionContentType.id)}
                                                            documentTypeCode="CONT_EVD"
                                                            title="Attach Containment Evidence"
                                                            compact
                                                        />
                                                    </div>
                                                )}
                                            </CollapsibleContent>
                                        </Collapsible>

                                        {/* Customer Approval Section */}
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
                                                        render={({ field }) => (
                                                            <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                                                <FormControl>
                                                                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
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
                                                        render={({ field }) => (
                                                            <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                                                <FormControl>
                                                                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
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
                                                    render={({ field }) => (
                                                        <FormItem>
                                                            <FormLabel>Approval Reference</FormLabel>
                                                            <FormControl>
                                                                <Input placeholder="PO#, email reference, or approval document number" {...field} />
                                                            </FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                                <FormField
                                                    control={control}
                                                    name="customer_approval_date"
                                                    render={({ field }) => (
                                                        <FormItem className="flex flex-col">
                                                            <FormLabel>Approval Date</FormLabel>
                                                            <Popover>
                                                                <PopoverTrigger asChild>
                                                                    <FormControl>
                                                                        <Button variant="outline" className={cn("w-[240px] pl-3 text-left font-normal", !field.value && "text-muted-foreground")}>
                                                                            {field.value ? format(new Date(field.value), "PPP") : <span>Pick a date</span>}
                                                                            <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                                        </Button>
                                                                    </FormControl>
                                                                </PopoverTrigger>
                                                                <PopoverContent className="w-auto p-0" align="start">
                                                                    <Calendar
                                                                        mode="single"
                                                                        selected={field.value ? new Date(field.value) : undefined}
                                                                        onSelect={(date) => field.onChange(date?.toISOString())}
                                                                        initialFocus
                                                                    />
                                                                </PopoverContent>
                                                            </Popover>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                                {/* Document upload for customer approval evidence */}
                                                {mode === "edit" && dispositionId && dispositionContentType && (
                                                    <div className="pt-2 border-t">
                                                        <DocumentUploader
                                                            objectId={dispositionId}
                                                            contentType={String(dispositionContentType.id)}
                                                            documentTypeCode="CUST_APPR"
                                                            title="Attach Approval Evidence"
                                                            compact
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Resolution Notes */}
                                        <FormField
                                            control={control}
                                            name="resolution_notes"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel required={required.resolution_notes}>Resolution Notes</FormLabel>
                                                    <FormControl>
                                                        <Textarea placeholder="Add resolution notes..." className="resize-none" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Resolution Completed By/At */}
                                        <div className="grid gap-4 md:grid-cols-2">
                                            <FormField
                                                control={control}
                                                name="resolution_completed_by"
                                                render={({ field }) => (
                                                    <FormItem className="flex flex-col">
                                                        <FormLabel>Resolution Completed By</FormLabel>
                                                        <Popover open={completedByPopoverOpen} onOpenChange={setCompletedByPopoverOpen}>
                                                            <PopoverTrigger asChild>
                                                                <FormControl>
                                                                    <Button variant="outline" role="combobox" className="w-full justify-between">
                                                                        {field.value
                                                                            ? `${employees.find((emp) => emp.id === field.value)?.first_name} ${employees.find((emp) => emp.id === field.value)?.last_name}`
                                                                            : "Select employee"
                                                                        }
                                                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                    </Button>
                                                                </FormControl>
                                                            </PopoverTrigger>
                                                            <PopoverContent className="w-full p-0">
                                                                <Command>
                                                                    <CommandInput placeholder="Search..." value={completedBySearch} onValueChange={setCompletedBySearch} />
                                                                    <CommandList>
                                                                        <CommandEmpty>No employees found.</CommandEmpty>
                                                                        <CommandGroup className="max-h-64 overflow-auto">
                                                                            {filteredCompletedBy.map((emp) => (
                                                                                <CommandItem
                                                                                    key={emp.id}
                                                                                    onSelect={() => {
                                                                                        field.onChange(emp.id)
                                                                                        setCompletedByPopoverOpen(false)
                                                                                    }}
                                                                                >
                                                                                    <Check className={cn("mr-2 h-4 w-4", field.value === emp.id ? "opacity-100" : "opacity-0")} />
                                                                                    {emp.first_name} {emp.last_name}
                                                                                </CommandItem>
                                                                            ))}
                                                                        </CommandGroup>
                                                                    </CommandList>
                                                                </Command>
                                                            </PopoverContent>
                                                        </Popover>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                            <FormField
                                                control={control}
                                                name="resolution_completed_at"
                                                render={({ field }) => (
                                                    <FormItem className="flex flex-col">
                                                        <FormLabel>Resolution Completed At</FormLabel>
                                                        <Popover>
                                                            <PopoverTrigger asChild>
                                                                <FormControl>
                                                                    <Button variant="outline" className={cn("w-full pl-3 text-left font-normal", !field.value && "text-muted-foreground")}>
                                                                        {field.value ? format(new Date(field.value), "PPP") : <span>Pick a date</span>}
                                                                        <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                                    </Button>
                                                                </FormControl>
                                                            </PopoverTrigger>
                                                            <PopoverContent className="w-auto p-0" align="start">
                                                                <Calendar
                                                                    mode="single"
                                                                    selected={field.value ? new Date(field.value) : undefined}
                                                                    onSelect={(date) => field.onChange(date?.toISOString())}
                                                                    initialFocus
                                                                />
                                                            </PopoverContent>
                                                        </Popover>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>

                                        {/* Related Part */}
                                        <FormField
                                            control={control}
                                            name="part"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel required={required.part}>Related Part</FormLabel>
                                                    <Popover open={partPopoverOpen} onOpenChange={setPartPopoverOpen}>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button variant="outline" role="combobox" className="w-full justify-between">
                                                                    {field.value
                                                                        ? parts.find((p) => p.id === field.value)?.ERP_id || `Part #${field.value}`
                                                                        : "Select part"
                                                                    }
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-full p-0">
                                                            <Command>
                                                                <CommandInput placeholder="Search parts..." value={partSearch} onValueChange={setPartSearch} />
                                                                <CommandList>
                                                                    <CommandEmpty>No parts found.</CommandEmpty>
                                                                    <CommandGroup className="max-h-64 overflow-auto">
                                                                        {parts.map((p) => (
                                                                            <CommandItem
                                                                                key={p.id}
                                                                                onSelect={() => {
                                                                                    field.onChange(p.id)
                                                                                    setPartPopoverOpen(false)
                                                                                }}
                                                                            >
                                                                                <Check className={cn("mr-2 h-4 w-4", field.value === p.id ? "opacity-100" : "opacity-0")} />
                                                                                {p.ERP_id} - {p.part_type_name}
                                                                            </CommandItem>
                                                                        ))}
                                                                    </CommandGroup>
                                                                </CommandList>
                                                            </Command>
                                                        </PopoverContent>
                                                    </Popover>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Quality Reports */}
                                        <FormField
                                            control={control}
                                            name="quality_reports"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel required={required.quality_reports}>Quality Reports</FormLabel>
                                                    <Popover open={qualityReportsPopoverOpen} onOpenChange={setQualityReportsPopoverOpen}>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button variant="outline" role="combobox" className="w-full justify-between">
                                                                    {field.value && field.value.length > 0
                                                                        ? `${field.value.length} report${field.value.length > 1 ? "s" : ""} selected`
                                                                        : "Select quality reports"
                                                                    }
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-full p-0">
                                                            <Command>
                                                                <CommandInput placeholder="Search quality reports..." value={qualityReportSearch} onValueChange={setQualityReportSearch} />
                                                                <CommandList>
                                                                    <CommandEmpty>No quality reports found.</CommandEmpty>
                                                                    <CommandGroup className="max-h-64 overflow-auto">
                                                                        {qualityReports.map((qr) => (
                                                                            <CommandItem
                                                                                key={qr.id}
                                                                                onSelect={() => {
                                                                                    const currentValue = field.value || []
                                                                                    const newValue = currentValue.includes(qr.id)
                                                                                        ? currentValue.filter((id) => id !== qr.id)
                                                                                        : [...currentValue, qr.id]
                                                                                    field.onChange(newValue)
                                                                                }}
                                                                            >
                                                                                <Check className={cn("mr-2 h-4 w-4", field.value?.includes(qr.id) ? "opacity-100" : "opacity-0")} />
                                                                                Report #{qr.id} - Part #{qr.part} - {qr.created_at ? format(new Date(qr.created_at), "MMM dd, yyyy") : "No date"}
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
                                                                {field.value.map((id) => {
                                                                    const report = qualityReports.find((qr) => qr.id === id)
                                                                    return (
                                                                        <li key={id} className="flex items-center gap-2">
                                                                            <span className="font-mono">#{id}</span>
                                                                            {report && (
                                                                                <>
                                                                                    <span>-</span>
                                                                                    <Badge variant={report.status === "FAIL" ? "destructive" : "default"} className="text-xs">
                                                                                        {report.status}
                                                                                    </Badge>
                                                                                </>
                                                                            )}
                                                                        </li>
                                                                    )
                                                                })}
                                                            </ul>
                                                        </div>
                                                    )}
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        {/* Submit Button */}
                                        <div className="flex justify-end gap-2 pt-4 border-t">
                                            <Button type="button" variant="outline" onClick={() => navigate({ to: "/production/dispositions" })}>
                                                Cancel
                                            </Button>
                                            <Button type="submit" disabled={isSubmitting}>
                                                {isSubmitting ? (
                                                    <>
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                        {mode === "edit" ? "Updating..." : "Creating..."}
                                                    </>
                                                ) : (
                                                    mode === "edit" ? "Update Disposition" : "Create Disposition"
                                                )}
                                            </Button>
                                        </div>
                                    </form>
                                </Form>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Context Panel (1/3 width) */}
                    <div className="space-y-4">
                        {/* Part Information Card */}
                        {part && (
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm">Part Information</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">ERP ID:</span>
                                        <span className="font-mono">{part.ERP_id}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Type:</span>
                                        <span>{part.part_type_name}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Status:</span>
                                        <Badge variant="outline">{part.part_status?.replace("_", " ")}</Badge>
                                    </div>
                                    {part.order_name && (
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Order:</span>
                                            <span>{part.order_name}</span>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Quality Reports Card */}
                        {mode === "edit" && disposition?.quality_reports && disposition.quality_reports.length > 0 && (
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm">Quality Reports ({disposition.quality_reports.length})</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-2">
                                    {disposition.quality_reports.map((qrId: string) => {
                                        const qr = qualityReports.find((r) => r.id === qrId)
                                        return (
                                            <div key={qrId} className="flex justify-between items-center text-sm">
                                                <span className="font-mono">#{qrId}</span>
                                                {qr && (
                                                    <Badge variant={qr.status === "FAIL" ? "destructive" : "default"}>
                                                        {qr.status}
                                                    </Badge>
                                                )}
                                            </div>
                                        )
                                    })}
                                </CardContent>
                            </Card>
                        )}

                        {/* 3D Annotation Status Card */}
                        {mode === "edit" && disposition && (
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm">3D Annotations</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {disposition.annotation_status?.has_pending ? (
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-destructive">
                                                <AlertTriangle className="h-4 w-4" />
                                                <span className="text-sm">{disposition.annotation_status.pending_count} pending</span>
                                            </div>
                                            <Link to="/annotator">
                                                <Button size="sm" variant="outline" className="w-full gap-2">
                                                    <ExternalLink className="h-4 w-4" />
                                                    Go to Annotator
                                                </Button>
                                            </Link>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-green-600">
                                            <CheckCircle className="h-4 w-4" />
                                            <span className="text-sm">All complete</span>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Documents Card */}
                        {mode === "edit" && disposition?.documents && disposition.documents.length > 0 && (
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm">Attached Documents ({disposition.documents.length})</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-2">
                                    {disposition.documents.map((doc: { id: string; file_url: string; file_name: string }) => (
                                        <div key={doc.id} className="flex items-center gap-2 text-sm">
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                            <a href={doc.file_url} target="_blank" rel="noopener noreferrer" className="hover:underline truncate">
                                                {doc.file_name}
                                            </a>
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>
                        )}

                        {/* Empty state for create mode without part */}
                        {!part && mode === "create" && (
                            <Card>
                                <CardContent className="py-6 text-center text-muted-foreground text-sm">
                                    Select a part to see its details
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
