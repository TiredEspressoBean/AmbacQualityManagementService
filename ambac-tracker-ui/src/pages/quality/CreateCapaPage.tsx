"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { format } from "date-fns"
import { useNavigate, useSearch } from "@tanstack/react-router"

import { cn } from "@/lib/utils"
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar as CalendarIcon, Check, ChevronsUpDown, ArrowLeft } from "lucide-react"
import { Calendar } from "@/components/ui/calendar"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { Link } from "@tanstack/react-router"

import { useCreateCapa } from "@/hooks/useCreateCapa"
import { useCreateRcaRecord } from "@/hooks/useCreateRcaRecord"
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers"
import { useRetrieveParts } from "@/hooks/useRetrieveParts"
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps"
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders"
import { useQualityReports } from "@/hooks/useQualityReports"
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions"
import { schemas } from "@/lib/api/generated"
import { Badge } from "@/components/ui/badge"
import { isFieldRequired } from "@/lib/zod-config"
import { X, ChevronDown, ChevronUp } from "lucide-react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"

// Get options from generated schemas, then create fresh enums for form validation
const CAPA_TYPE_OPTIONS = schemas.CapaTypeEnum.options
const CAPA_SEVERITY_OPTIONS = schemas.SeverityEnum.options
// Only supporting these two RCA methods for now (subset of schemas.RcaMethodEnum.options)
const RCA_METHOD_OPTIONS = schemas.RcaMethodEnum.options.filter(
    (m): m is "FIVE_WHYS" | "FISHBONE" => m === "FIVE_WHYS" || m === "FISHBONE"
)

// Fresh zod enums to avoid type mismatch with Select component
const capaTypeEnum = z.enum(CAPA_TYPE_OPTIONS)
const capaSeverityEnum = z.enum(CAPA_SEVERITY_OPTIONS)
const rcaMethodEnum = z.enum(RCA_METHOD_OPTIONS)

const capaTypeLabels: Record<string, string> = {
    CORRECTIVE: "Corrective Action",
    PREVENTIVE: "Preventive Action",
    CUSTOMER_COMPLAINT: "Customer Complaint",
    INTERNAL_AUDIT: "Internal Audit Finding",
    SUPPLIER: "Supplier Issue",
}

const severityLabels: Record<string, string> = {
    CRITICAL: "Critical",
    MAJOR: "Major",
    MINOR: "Minor",
}

const rcaMethodLabels: Record<string, string> = {
    FIVE_WHYS: "5 Whys Analysis",
    FISHBONE: "Fishbone (Ishikawa) Diagram",
}

const formSchema = z.object({
    capa_type: capaTypeEnum,
    severity: capaSeverityEnum,
    problem_statement: z.string().min(1, "Problem statement is required"),
    immediate_action: z.string().nullish(),
    assigned_to: z.number().int().nullish(),
    due_date: z.date().nullish(),
    allow_self_verification: z.boolean().optional(),
    part: z.string().nullish(),
    step: z.string().nullish(),
    work_order: z.string().nullish(),
    quality_reports: z.array(z.string()).optional(),
    dispositions: z.array(z.string()).optional(),
    // RCA fields
    rca_method: rcaMethodEnum.nullish(),
    rca_problem_description: z.string().nullish(),
    // 5 Whys fields
    why_1_question: z.string().nullish(),
    why_1_answer: z.string().nullish(),
    why_2_question: z.string().nullish(),
    why_2_answer: z.string().nullish(),
    why_3_question: z.string().nullish(),
    why_3_answer: z.string().nullish(),
    why_4_question: z.string().nullish(),
    why_4_answer: z.string().nullish(),
    why_5_question: z.string().nullish(),
    why_5_answer: z.string().nullish(),
    identified_root_cause: z.string().nullish(),
    // Fishbone fields
    fishbone_problem_statement: z.string().nullish(),
    man_causes: z.string().nullish(),
    machine_causes: z.string().nullish(),
    material_causes: z.string().nullish(),
    method_causes: z.string().nullish(),
    measurement_causes: z.string().nullish(),
    environment_causes: z.string().nullish(),
    fishbone_root_cause: z.string().nullish(),
})

type FormValues = z.infer<typeof formSchema>

const required = {
    capa_type: isFieldRequired(formSchema.shape.capa_type),
    severity: isFieldRequired(formSchema.shape.severity),
    problem_statement: isFieldRequired(formSchema.shape.problem_statement),
}

// Search params type for URL query parameters
type CreateCapaSearchParams = {
    quality_reports?: string
}

// Simple debounce hook
function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value)

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedValue(value), delay)
        return () => clearTimeout(timer)
    }, [value, delay])

    return debouncedValue
}

export function CreateCapaPage() {
    const navigate = useNavigate()
    const searchParams = useSearch({ strict: false }) as CreateCapaSearchParams

    // Immediate search values (what the user types)
    const [userSearch, setUserSearch] = useState("")
    const [partSearch, setPartSearch] = useState("")
    const [stepSearch, setStepSearch] = useState("")
    const [workOrderSearch, setWorkOrderSearch] = useState("")
    const [qualityReportSearch, setQualityReportSearch] = useState("")
    const [dispositionSearch, setDispositionSearch] = useState("")

    // Debounced search values (what hits the API) - 300ms delay
    const debouncedUserSearch = useDebounce(userSearch, 300)
    const debouncedPartSearch = useDebounce(partSearch, 300)
    const debouncedStepSearch = useDebounce(stepSearch, 300)
    const debouncedWorkOrderSearch = useDebounce(workOrderSearch, 300)
    const debouncedQualityReportSearch = useDebounce(qualityReportSearch, 300)
    const debouncedDispositionSearch = useDebounce(dispositionSearch, 300)

    // Parse quality_reports from URL query param (can be single ID or comma-separated IDs)
    const parseQualityReports = (): string[] => {
        const qr = searchParams.quality_reports
        if (!qr) return []
        // Handle if it's already an array (some routers do this)
        if (Array.isArray(qr)) {
            return qr.map(id => String(id)).filter(id => id.length > 0)
        }
        // Handle string (single ID or comma-separated)
        if (typeof qr === 'string') {
            return qr.split(',').map(id => id.trim()).filter(id => id.length > 0)
        }
        // Handle single value
        if (typeof qr === 'number' || typeof qr === 'string') {
            return [String(qr)]
        }
        return []
    }
    const initialQualityReports = parseQualityReports()

    // Use debounced values for API calls to avoid excessive requests
    const { data: users } = useRetrieveUsers({ search: debouncedUserSearch, limit: 50 })
    const { data: parts } = useRetrieveParts({ search: debouncedPartSearch, limit: 50 })
    const { data: steps } = useRetrieveSteps({ search: debouncedStepSearch, limit: 50 })
    const { data: workOrders } = useRetrieveWorkOrders({ search: debouncedWorkOrderSearch, limit: 50 })
    const { data: qualityReports } = useQualityReports({ search: debouncedQualityReportSearch, limit: 50 })
    const { data: dispositions } = useRetrieveQuarantineDispositions({ search: debouncedDispositionSearch, limit: 50 }, { enabled: true })
    const createCapa = useCreateCapa()
    const createRcaRecord = useCreateRcaRecord()

    // RCA section state
    const [rcaOpen, setRcaOpen] = useState(false)

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            capa_type: undefined,
            severity: undefined,
            problem_statement: "",
            immediate_action: null,
            assigned_to: null,
            due_date: null,
            allow_self_verification: false,
            part: null,
            step: null,
            work_order: null,
            quality_reports: initialQualityReports,
            dispositions: [],
            // RCA defaults
            rca_method: null,
            rca_problem_description: null,
            why_1_question: null,
            why_1_answer: null,
            why_2_question: null,
            why_2_answer: null,
            why_3_question: null,
            why_3_answer: null,
            why_4_question: null,
            why_4_answer: null,
            why_5_question: null,
            why_5_answer: null,
            identified_root_cause: null,
            fishbone_problem_statement: null,
            man_causes: null,
            machine_causes: null,
            material_causes: null,
            method_causes: null,
            measurement_causes: null,
            environment_causes: null,
            fishbone_root_cause: null,
        },
    })

    // Watch RCA method for conditional rendering
    const rcaMethod = form.watch("rca_method")

    // Update quality_reports if URL param changes
    useEffect(() => {
        if (initialQualityReports.length > 0) {
            form.setValue("quality_reports", initialQualityReports)
        }
    }, [searchParams.quality_reports])

    // Check for pre-filled problem statement from SPC page
    useEffect(() => {
        const spcProblemStatement = sessionStorage.getItem('spc_capa_problem_statement')
        if (spcProblemStatement) {
            form.setValue("problem_statement", spcProblemStatement)
            form.setValue("capa_type", "CORRECTIVE")
            sessionStorage.removeItem('spc_capa_problem_statement')
        }
    }, [])

    function onSubmit(values: z.infer<typeof formSchema>) {
        // Extract RCA-specific fields from the form values
        const {
            rca_method,
            rca_problem_description,
            why_1_question, why_1_answer,
            why_2_question, why_2_answer,
            why_3_question, why_3_answer,
            why_4_question, why_4_answer,
            why_5_question, why_5_answer,
            identified_root_cause,
            fishbone_problem_statement,
            man_causes, machine_causes, material_causes,
            method_causes, measurement_causes, environment_causes,
            fishbone_root_cause,
            ...capaFields
        } = values

        const capaPayload = {
            ...capaFields,
            due_date: capaFields.due_date ? format(capaFields.due_date, "yyyy-MM-dd") : null,
            immediate_action: capaFields.immediate_action || null,
            assigned_to: capaFields.assigned_to || null,
        }

        createCapa.mutate(capaPayload, {
            onSuccess: (capaData) => {
                // If RCA method is selected, create the RCA record
                if (rca_method) {
                    const rcaPayload: Record<string, unknown> = {
                        capa: capaData.id,
                        rca_method: rca_method,
                        problem_description: rca_problem_description || values.problem_statement,
                    }

                    // Add Five Whys data if method is FIVE_WHYS
                    if (rca_method === "FIVE_WHYS") {
                        rcaPayload.five_whys_data = {
                            why_1_question: why_1_question || null,
                            why_1_answer: why_1_answer || null,
                            why_2_question: why_2_question || null,
                            why_2_answer: why_2_answer || null,
                            why_3_question: why_3_question || null,
                            why_3_answer: why_3_answer || null,
                            why_4_question: why_4_question || null,
                            why_4_answer: why_4_answer || null,
                            why_5_question: why_5_question || null,
                            why_5_answer: why_5_answer || null,
                            identified_root_cause: identified_root_cause || null,
                        }
                    }

                    // Add Fishbone data if method is FISHBONE
                    if (rca_method === "FISHBONE") {
                        rcaPayload.fishbone_data = {
                            problem_statement: fishbone_problem_statement || null,
                            man_causes: man_causes || null,
                            machine_causes: machine_causes || null,
                            material_causes: material_causes || null,
                            method_causes: method_causes || null,
                            measurement_causes: measurement_causes || null,
                            environment_causes: environment_causes || null,
                            identified_root_cause: fishbone_root_cause || null,
                        }
                    }

                    createRcaRecord.mutate(rcaPayload as Parameters<typeof createRcaRecord.mutate>[0], {
                        onSuccess: () => {
                            toast.success("CAPA and RCA created successfully!")
                            navigate({ to: "/quality/capas/$id", params: { id: String(capaData.id) } })
                        },
                        onError: (error) => {
                            // CAPA was created but RCA failed - still navigate but warn
                            toast.warning("CAPA created, but RCA creation failed. You can add RCA from the detail page.")
                            console.error("Create RCA error:", error)
                            navigate({ to: "/quality/capas/$id", params: { id: String(capaData.id) } })
                        },
                    })
                } else {
                    toast.success("CAPA created successfully!")
                    navigate({ to: "/quality/capas/$id", params: { id: String(capaData.id) } })
                }
            },
            onError: (error) => {
                toast.error("Failed to create CAPA")
                console.error("Create CAPA error:", error)
            },
        })
    }

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            <div className="mb-6">
                <Button asChild variant="ghost" size="sm">
                    <Link to="/quality/capas">
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Back to CAPAs
                    </Link>
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Create New CAPA</CardTitle>
                    <CardDescription>
                        Create a Corrective and Preventive Action to address quality issues.
                        Required fields are marked with *.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            {/* Type and Severity Row */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <FormField
                                    control={form.control}
                                    name="capa_type"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel required={required.capa_type}>CAPA Type</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select type" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {CAPA_TYPE_OPTIONS.map((type) => (
                                                        <SelectItem key={type} value={type}>
                                                            {capaTypeLabels[type] || type}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormDescription>
                                                What type of action is this?
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
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
                                                    {CAPA_SEVERITY_OPTIONS.map((severity) => (
                                                        <SelectItem key={severity} value={severity}>
                                                            {severityLabels[severity] || severity}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormDescription>
                                                Critical/Major require approval before closure
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            {/* Problem Statement */}
                            <FormField
                                control={form.control}
                                name="problem_statement"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.problem_statement}>Problem Statement</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                placeholder="Clearly describe the problem or issue that needs to be addressed..."
                                                className="min-h-[120px] resize-y"
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            Be specific: What happened? When? Where? What is the impact?
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            {/* Immediate Action */}
                            <FormField
                                control={form.control}
                                name="immediate_action"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Immediate/Containment Action</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                placeholder="What actions were taken immediately to contain the issue? (optional)"
                                                className="min-h-[80px] resize-y"
                                                {...field}
                                                value={field.value || ""}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            Document any immediate containment actions already taken
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <Separator />

                            {/* Assignment Row */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <FormField
                                    control={form.control}
                                    name="assigned_to"
                                    render={({ field }) => {
                                        const selectedUser = users?.results?.find((u) => u.id === field.value)
                                        return (
                                            <FormItem className="flex flex-col">
                                                <FormLabel>Assigned To</FormLabel>
                                                <Popover>
                                                    <PopoverTrigger asChild>
                                                        <FormControl>
                                                            <Button
                                                                variant="outline"
                                                                role="combobox"
                                                                className={cn(
                                                                    "justify-between",
                                                                    !field.value && "text-muted-foreground"
                                                                )}
                                                            >
                                                                {selectedUser?.username || selectedUser?.email || "Select assignee (optional)"}
                                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                            </Button>
                                                        </FormControl>
                                                    </PopoverTrigger>
                                                    <PopoverContent className="w-[300px] p-0">
                                                        <Command>
                                                            <CommandInput
                                                                value={userSearch}
                                                                onValueChange={setUserSearch}
                                                                placeholder="Search users..."
                                                            />
                                                            <CommandList>
                                                                <CommandEmpty>No users found.</CommandEmpty>
                                                                <CommandGroup>
                                                                    {users?.results?.map((user) => (
                                                                        <CommandItem
                                                                            key={user.id}
                                                                            value={user.username || user.email}
                                                                            onSelect={() => {
                                                                                form.setValue("assigned_to", user.id)
                                                                            }}
                                                                        >
                                                                            <Check
                                                                                className={cn(
                                                                                    "mr-2 h-4 w-4",
                                                                                    user.id === field.value ? "opacity-100" : "opacity-0"
                                                                                )}
                                                                            />
                                                                            {user.username || user.email}
                                                                        </CommandItem>
                                                                    ))}
                                                                </CommandGroup>
                                                            </CommandList>
                                                        </Command>
                                                    </PopoverContent>
                                                </Popover>
                                                <FormDescription>
                                                    Who is responsible for this CAPA?
                                                </FormDescription>
                                                <FormMessage />
                                            </FormItem>
                                        )
                                    }}
                                />

                                <FormField
                                    control={form.control}
                                    name="due_date"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-col">
                                            <FormLabel>Due Date</FormLabel>
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <FormControl>
                                                        <Button
                                                            variant="outline"
                                                            className={cn(
                                                                "pl-3 text-left font-normal",
                                                                !field.value && "text-muted-foreground"
                                                            )}
                                                        >
                                                            {field.value ? format(field.value, "PPP") : "Select due date (optional)"}
                                                            <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                        </Button>
                                                    </FormControl>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-auto p-0" align="start">
                                                    <Calendar
                                                        mode="single"
                                                        selected={field.value || undefined}
                                                        onSelect={field.onChange}
                                                        disabled={(date) => date < new Date()}
                                                        initialFocus
                                                    />
                                                </PopoverContent>
                                            </Popover>
                                            <FormDescription>
                                                When should this CAPA be completed?
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <Separator />

                            {/* Related Items Section */}
                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-medium">Related Items</h3>
                                    <p className="text-sm text-muted-foreground">
                                        Link this CAPA to specific parts, process steps, or work orders (all optional)
                                    </p>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    {/* Part */}
                                    <FormField
                                        control={form.control}
                                        name="part"
                                        render={({ field }) => {
                                            const selectedPart = parts?.results?.find((p) => p.id === field.value)
                                            return (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel>Part</FormLabel>
                                                    <Popover>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button
                                                                    variant="outline"
                                                                    role="combobox"
                                                                    className={cn(
                                                                        "justify-between",
                                                                        !field.value && "text-muted-foreground"
                                                                    )}
                                                                >
                                                                    {selectedPart?.ERP_id || "Select part"}
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-[250px] p-0">
                                                            <Command shouldFilter={false}>
                                                                <CommandInput
                                                                    value={partSearch}
                                                                    onValueChange={setPartSearch}
                                                                    placeholder="Search parts by ERP ID..."
                                                                />
                                                                <CommandList>
                                                                    <CommandEmpty>No parts found.</CommandEmpty>
                                                                    <CommandGroup>
                                                                        {parts?.results?.map((part) => (
                                                                            <CommandItem
                                                                                key={part.id}
                                                                                value={String(part.id)}
                                                                                onSelect={() => {
                                                                                    form.setValue("part", part.id)
                                                                                }}
                                                                            >
                                                                                <Check
                                                                                    className={cn(
                                                                                        "mr-2 h-4 w-4",
                                                                                        part.id === field.value ? "opacity-100" : "opacity-0"
                                                                                    )}
                                                                                />
                                                                                {part.ERP_id}
                                                                            </CommandItem>
                                                                        ))}
                                                                    </CommandGroup>
                                                                </CommandList>
                                                            </Command>
                                                        </PopoverContent>
                                                    </Popover>
                                                    <FormMessage />
                                                </FormItem>
                                            )
                                        }}
                                    />

                                    {/* Step */}
                                    <FormField
                                        control={form.control}
                                        name="step"
                                        render={({ field }) => {
                                            const selectedStep = steps?.results?.find((s) => s.id === field.value)
                                            return (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel>Process Step</FormLabel>
                                                    <Popover>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button
                                                                    variant="outline"
                                                                    role="combobox"
                                                                    className={cn(
                                                                        "justify-between",
                                                                        !field.value && "text-muted-foreground"
                                                                    )}
                                                                >
                                                                    {selectedStep?.name || "Select step"}
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-[250px] p-0">
                                                            <Command>
                                                                <CommandInput
                                                                    value={stepSearch}
                                                                    onValueChange={setStepSearch}
                                                                    placeholder="Search steps..."
                                                                />
                                                                <CommandList>
                                                                    <CommandEmpty>No steps found.</CommandEmpty>
                                                                    <CommandGroup>
                                                                        {steps?.results?.map((step) => (
                                                                            <CommandItem
                                                                                key={step.id}
                                                                                value={step.name}
                                                                                onSelect={() => {
                                                                                    form.setValue("step", step.id)
                                                                                }}
                                                                            >
                                                                                <Check
                                                                                    className={cn(
                                                                                        "mr-2 h-4 w-4",
                                                                                        step.id === field.value ? "opacity-100" : "opacity-0"
                                                                                    )}
                                                                                />
                                                                                {step.name}
                                                                            </CommandItem>
                                                                        ))}
                                                                    </CommandGroup>
                                                                </CommandList>
                                                            </Command>
                                                        </PopoverContent>
                                                    </Popover>
                                                    <FormMessage />
                                                </FormItem>
                                            )
                                        }}
                                    />

                                    {/* Work Order */}
                                    <FormField
                                        control={form.control}
                                        name="work_order"
                                        render={({ field }) => {
                                            const selectedWorkOrder = workOrders?.results?.find((w) => w.id === field.value)
                                            return (
                                                <FormItem className="flex flex-col">
                                                    <FormLabel>Work Order</FormLabel>
                                                    <Popover>
                                                        <PopoverTrigger asChild>
                                                            <FormControl>
                                                                <Button
                                                                    variant="outline"
                                                                    role="combobox"
                                                                    className={cn(
                                                                        "justify-between",
                                                                        !field.value && "text-muted-foreground"
                                                                    )}
                                                                >
                                                                    {selectedWorkOrder?.ERP_id || "Select work order"}
                                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                                </Button>
                                                            </FormControl>
                                                        </PopoverTrigger>
                                                        <PopoverContent className="w-[250px] p-0">
                                                            <Command>
                                                                <CommandInput
                                                                    value={workOrderSearch}
                                                                    onValueChange={setWorkOrderSearch}
                                                                    placeholder="Search work orders..."
                                                                />
                                                                <CommandList>
                                                                    <CommandEmpty>No work orders found.</CommandEmpty>
                                                                    <CommandGroup>
                                                                        {workOrders?.results?.map((wo) => (
                                                                            <CommandItem
                                                                                key={wo.id}
                                                                                value={wo.ERP_id}
                                                                                onSelect={() => {
                                                                                    form.setValue("work_order", wo.id)
                                                                                }}
                                                                            >
                                                                                <Check
                                                                                    className={cn(
                                                                                        "mr-2 h-4 w-4",
                                                                                        wo.id === field.value ? "opacity-100" : "opacity-0"
                                                                                    )}
                                                                                />
                                                                                {wo.ERP_id}
                                                                            </CommandItem>
                                                                        ))}
                                                                    </CommandGroup>
                                                                </CommandList>
                                                            </Command>
                                                        </PopoverContent>
                                                    </Popover>
                                                    <FormMessage />
                                                </FormItem>
                                            )
                                        }}
                                    />
                                </div>
                            </div>

                            <Separator />

                            {/* Quality Reports Section */}
                            <FormField
                                control={form.control}
                                name="quality_reports"
                                render={({ field }) => {
                                    const selectedReports = field.value || []
                                    const toggleReport = (reportId: string) => {
                                        if (selectedReports.includes(reportId)) {
                                            form.setValue("quality_reports", selectedReports.filter(id => id !== reportId))
                                        } else {
                                            form.setValue("quality_reports", [...selectedReports, reportId])
                                        }
                                    }
                                    const removeReport = (reportId: string) => {
                                        form.setValue("quality_reports", selectedReports.filter(id => id !== reportId))
                                    }

                                    return (
                                        <FormItem className="space-y-4">
                                            <div>
                                                <FormLabel className="text-lg font-medium">Linked Quality Reports</FormLabel>
                                                <FormDescription>
                                                    Link NCRs and quality reports to this CAPA
                                                </FormDescription>
                                            </div>

                                            {/* Selected reports display */}
                                            {selectedReports.length > 0 && (
                                                <div className="flex flex-wrap gap-2">
                                                    {selectedReports.map((reportId) => {
                                                        const report = qualityReports?.results?.find(r => r.id === reportId)
                                                        return (
                                                            <Badge
                                                                key={reportId}
                                                                variant="secondary"
                                                                className="flex items-center gap-1 px-2 py-1"
                                                            >
                                                                <span>
                                                                    {report ? `#${reportId} - ${report.status}` : `Report #${reportId}`}
                                                                </span>
                                                                <button
                                                                    type="button"
                                                                    onClick={() => removeReport(reportId)}
                                                                    className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                                                                >
                                                                    <X className="h-3 w-3" />
                                                                </button>
                                                            </Badge>
                                                        )
                                                    })}
                                                </div>
                                            )}

                                            {/* Searchable dropdown to add reports */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <FormControl>
                                                        <Button
                                                            variant="outline"
                                                            role="combobox"
                                                            className={cn(
                                                                "w-full justify-between",
                                                                selectedReports.length === 0 && "text-muted-foreground"
                                                            )}
                                                        >
                                                            {selectedReports.length > 0
                                                                ? `${selectedReports.length} report${selectedReports.length > 1 ? 's' : ''} selected`
                                                                : "Search and add quality reports..."
                                                            }
                                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                        </Button>
                                                    </FormControl>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[400px] p-0" align="start">
                                                    <Command shouldFilter={false}>
                                                        <CommandInput
                                                            value={qualityReportSearch}
                                                            onValueChange={setQualityReportSearch}
                                                            placeholder="Search quality reports by ID, status, or description..."
                                                        />
                                                        <CommandList>
                                                            <CommandEmpty>No quality reports found.</CommandEmpty>
                                                            <CommandGroup>
                                                                {qualityReports?.results?.map((report) => (
                                                                    <CommandItem
                                                                        key={report.id}
                                                                        value={String(report.id)}
                                                                        onSelect={() => toggleReport(report.id)}
                                                                    >
                                                                        <Check
                                                                            className={cn(
                                                                                "mr-2 h-4 w-4",
                                                                                selectedReports.includes(report.id) ? "opacity-100" : "opacity-0"
                                                                            )}
                                                                        />
                                                                        <div className="flex flex-col">
                                                                            <span className="font-medium">
                                                                                Report #{report.id} - {report.status}
                                                                            </span>
                                                                            <span className="text-xs text-muted-foreground">
                                                                                {report.description ? report.description.substring(0, 50) : 'No description'}
                                                                                {report.description && report.description.length > 50 ? '...' : ''}
                                                                            </span>
                                                                        </div>
                                                                    </CommandItem>
                                                                ))}
                                                            </CommandGroup>
                                                        </CommandList>
                                                    </Command>
                                                </PopoverContent>
                                            </Popover>
                                            <FormMessage />
                                        </FormItem>
                                    )
                                }}
                            />

                            <Separator />

                            {/* Dispositions Section */}
                            <FormField
                                control={form.control}
                                name="dispositions"
                                render={({ field }) => {
                                    const selectedDispositions = field.value || []
                                    const toggleDisposition = (dispositionId: string) => {
                                        if (selectedDispositions.includes(dispositionId)) {
                                            form.setValue("dispositions", selectedDispositions.filter(id => id !== dispositionId))
                                        } else {
                                            form.setValue("dispositions", [...selectedDispositions, dispositionId])
                                        }
                                    }
                                    const removeDisposition = (dispositionId: string) => {
                                        form.setValue("dispositions", selectedDispositions.filter(id => id !== dispositionId))
                                    }

                                    return (
                                        <FormItem className="space-y-4">
                                            <div>
                                                <FormLabel className="text-lg font-medium">Linked Dispositions</FormLabel>
                                                <FormDescription>
                                                    Link quarantine dispositions to this CAPA
                                                </FormDescription>
                                            </div>

                                            {/* Selected dispositions display */}
                                            {selectedDispositions.length > 0 && (
                                                <div className="flex flex-wrap gap-2">
                                                    {selectedDispositions.map((dispositionId) => {
                                                        const disposition = dispositions?.results?.find(d => d.id === dispositionId)
                                                        return (
                                                            <Badge
                                                                key={dispositionId}
                                                                variant="secondary"
                                                                className="flex items-center gap-1 px-2 py-1"
                                                            >
                                                                <span>
                                                                    {disposition ? `#${dispositionId} - ${disposition.disposition_type}` : `Disposition #${dispositionId}`}
                                                                </span>
                                                                <button
                                                                    type="button"
                                                                    onClick={() => removeDisposition(dispositionId)}
                                                                    className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                                                                >
                                                                    <X className="h-3 w-3" />
                                                                </button>
                                                            </Badge>
                                                        )
                                                    })}
                                                </div>
                                            )}

                                            {/* Searchable dropdown to add dispositions */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <FormControl>
                                                        <Button
                                                            variant="outline"
                                                            role="combobox"
                                                            className={cn(
                                                                "w-full justify-between",
                                                                selectedDispositions.length === 0 && "text-muted-foreground"
                                                            )}
                                                        >
                                                            {selectedDispositions.length > 0
                                                                ? `${selectedDispositions.length} disposition${selectedDispositions.length > 1 ? 's' : ''} selected`
                                                                : "Search and add dispositions..."
                                                            }
                                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                        </Button>
                                                    </FormControl>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[400px] p-0" align="start">
                                                    <Command>
                                                        <CommandInput
                                                            value={dispositionSearch}
                                                            onValueChange={setDispositionSearch}
                                                            placeholder="Search dispositions..."
                                                        />
                                                        <CommandList>
                                                            <CommandEmpty>No dispositions found.</CommandEmpty>
                                                            <CommandGroup>
                                                                {dispositions?.results?.map((disposition) => (
                                                                    <CommandItem
                                                                        key={disposition.id}
                                                                        value={`${disposition.id} ${disposition.disposition_type}`}
                                                                        onSelect={() => toggleDisposition(disposition.id)}
                                                                    >
                                                                        <Check
                                                                            className={cn(
                                                                                "mr-2 h-4 w-4",
                                                                                selectedDispositions.includes(disposition.id) ? "opacity-100" : "opacity-0"
                                                                            )}
                                                                        />
                                                                        <div className="flex flex-col">
                                                                            <span className="font-medium">
                                                                                Disposition #{disposition.id}
                                                                            </span>
                                                                            <span className="text-xs text-muted-foreground">
                                                                                Type: {disposition.disposition_type}
                                                                            </span>
                                                                        </div>
                                                                    </CommandItem>
                                                                ))}
                                                            </CommandGroup>
                                                        </CommandList>
                                                    </Command>
                                                </PopoverContent>
                                            </Popover>
                                            <FormMessage />
                                        </FormItem>
                                    )
                                }}
                            />

                            <Separator />

                            {/* Initial Root Cause Analysis Section */}
                            <Collapsible open={rcaOpen} onOpenChange={setRcaOpen}>
                                <CollapsibleTrigger asChild>
                                    <Button variant="ghost" className="w-full justify-between p-4 h-auto">
                                        <div className="text-left">
                                            <h3 className="text-lg font-medium">Initial Root Cause Analysis</h3>
                                            <p className="text-sm text-muted-foreground font-normal">
                                                Optionally start your RCA now using 5 Whys or Fishbone analysis
                                            </p>
                                        </div>
                                        {rcaOpen ? (
                                            <ChevronUp className="h-5 w-5 text-muted-foreground" />
                                        ) : (
                                            <ChevronDown className="h-5 w-5 text-muted-foreground" />
                                        )}
                                    </Button>
                                </CollapsibleTrigger>
                                <CollapsibleContent className="space-y-6 pt-4">
                                    {/* RCA Method Selection */}
                                    <FormField
                                        control={form.control}
                                        name="rca_method"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>RCA Method</FormLabel>
                                                <Select
                                                    onValueChange={field.onChange}
                                                    value={field.value || undefined}
                                                >
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Select analysis method" />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        {RCA_METHOD_OPTIONS.map((method) => (
                                                            <SelectItem key={method} value={method}>
                                                                {rcaMethodLabels[method] || method}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <FormDescription>
                                                    Choose your root cause analysis methodology
                                                </FormDescription>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    {/* Problem Description for RCA */}
                                    {rcaMethod && (
                                        <FormField
                                            control={form.control}
                                            name="rca_problem_description"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Problem Description for RCA</FormLabel>
                                                    <FormControl>
                                                        <Textarea
                                                            placeholder="Describe the problem to be analyzed..."
                                                            className="min-h-[80px] resize-y"
                                                            {...field}
                                                            value={field.value || ""}
                                                        />
                                                    </FormControl>
                                                    <FormDescription>
                                                        Specific problem statement for root cause analysis (can differ from the CAPA problem statement)
                                                    </FormDescription>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    )}

                                    {/* 5 Whys Fields */}
                                    {rcaMethod === "FIVE_WHYS" && (
                                        <div className="space-y-4 pl-4 border-l-2 border-primary/20">
                                            <h4 className="font-medium text-sm text-muted-foreground">5 Whys Analysis</h4>

                                            {[1, 2, 3, 4, 5].map((num) => (
                                                <div key={num} className="space-y-2 p-3 rounded-lg bg-muted/30">
                                                    <div className="flex items-center gap-2">
                                                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                                                            {num}
                                                        </span>
                                                        <span className="text-sm font-medium">Why #{num}</span>
                                                    </div>
                                                    <FormField
                                                        control={form.control}
                                                        name={`why_${num}_question` as keyof FormValues}
                                                        render={({ field }) => (
                                                            <FormItem>
                                                                <FormControl>
                                                                    <Input
                                                                        placeholder={num === 1 ? "Why did this happen?" : "Why? (follow up from previous answer)"}
                                                                        {...field}
                                                                        value={(field.value as string) || ""}
                                                                    />
                                                                </FormControl>
                                                            </FormItem>
                                                        )}
                                                    />
                                                    <FormField
                                                        control={form.control}
                                                        name={`why_${num}_answer` as keyof FormValues}
                                                        render={({ field }) => (
                                                            <FormItem>
                                                                <FormControl>
                                                                    <Textarea
                                                                        placeholder="Answer..."
                                                                        className="min-h-[60px] resize-y"
                                                                        {...field}
                                                                        value={(field.value as string) || ""}
                                                                    />
                                                                </FormControl>
                                                            </FormItem>
                                                        )}
                                                    />
                                                </div>
                                            ))}

                                            <FormField
                                                control={form.control}
                                                name="identified_root_cause"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Identified Root Cause</FormLabel>
                                                        <FormControl>
                                                            <Textarea
                                                                placeholder="Based on the 5 Whys analysis, what is the root cause?"
                                                                className="min-h-[80px] resize-y"
                                                                {...field}
                                                                value={field.value || ""}
                                                            />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>
                                    )}

                                    {/* Fishbone Fields */}
                                    {rcaMethod === "FISHBONE" && (
                                        <div className="space-y-4">
                                            <h4 className="font-medium text-sm text-muted-foreground">Fishbone (Ishikawa) Diagram - 6M Categories</h4>

                                            <FormField
                                                control={form.control}
                                                name="fishbone_problem_statement"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Problem Statement (Head of Fish)</FormLabel>
                                                        <FormControl>
                                                            <Input
                                                                placeholder="The effect/problem to analyze"
                                                                {...field}
                                                                value={field.value || ""}
                                                            />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />

                                            <p className="text-xs text-muted-foreground mb-2">
                                                Enter potential causes for each category. Separate multiple causes with new lines or commas.
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {[
                                                    { name: "man_causes", label: "Man (People)", placeholder: "Insufficient training\nOperator fatigue\nCommunication gaps" },
                                                    { name: "machine_causes", label: "Machine (Equipment)", placeholder: "Out of calibration\nWorn tooling\nInsufficient maintenance" },
                                                    { name: "material_causes", label: "Material", placeholder: "Out of spec material\nSupplier quality issue\nImproper storage" },
                                                    { name: "method_causes", label: "Method (Process)", placeholder: "Unclear work instructions\nProcess not followed\nNo standard procedure" },
                                                    { name: "measurement_causes", label: "Measurement", placeholder: "Gauge not calibrated\nWrong measurement method\nInspection skipped" },
                                                    { name: "environment_causes", label: "Environment", placeholder: "Temperature fluctuation\nContamination\nPoor lighting" },
                                                ].map(({ name, label, placeholder }) => (
                                                    <FormField
                                                        key={name}
                                                        control={form.control}
                                                        name={name as keyof FormValues}
                                                        render={({ field }) => (
                                                            <FormItem>
                                                                <FormLabel>{label}</FormLabel>
                                                                <FormControl>
                                                                    <Textarea
                                                                        placeholder={placeholder}
                                                                        className="min-h-[80px] resize-y"
                                                                        {...field}
                                                                        value={(field.value as string) || ""}
                                                                    />
                                                                </FormControl>
                                                            </FormItem>
                                                        )}
                                                    />
                                                ))}
                                            </div>

                                            <FormField
                                                control={form.control}
                                                name="fishbone_root_cause"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Identified Root Cause</FormLabel>
                                                        <FormControl>
                                                            <Textarea
                                                                placeholder="Based on the fishbone analysis, what is the root cause?"
                                                                className="min-h-[80px] resize-y"
                                                                {...field}
                                                                value={field.value || ""}
                                                            />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>
                                    )}
                                </CollapsibleContent>
                            </Collapsible>

                            <Separator />

                            {/* Options Section */}
                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-medium">Options</h3>
                                    <p className="text-sm text-muted-foreground">
                                        Configure verification and approval settings
                                    </p>
                                </div>

                                <FormField
                                    control={form.control}
                                    name="allow_self_verification"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                            <FormControl>
                                                <Checkbox
                                                    checked={field.value}
                                                    onCheckedChange={field.onChange}
                                                />
                                            </FormControl>
                                            <div className="space-y-1 leading-none">
                                                <FormLabel>
                                                    Allow Self-Verification
                                                </FormLabel>
                                                <FormDescription>
                                                    When enabled, the initiator or assignee may verify their own work.
                                                    Use for minor issues or when independent verification is not required.
                                                </FormDescription>
                                            </div>
                                        </FormItem>
                                    )}
                                />
                            </div>

                            {/* Submit */}
                            <div className="flex justify-end gap-4">
                                <Button type="button" variant="outline" asChild>
                                    <Link to="/quality/capas">Cancel</Link>
                                </Button>
                                <Button type="submit" disabled={createCapa.isPending || createRcaRecord.isPending}>
                                    {createCapa.isPending || createRcaRecord.isPending ? "Creating..." : "Create CAPA"}
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}