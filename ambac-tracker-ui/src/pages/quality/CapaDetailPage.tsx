import { useParams, Link } from "@tanstack/react-router"
import { useRetrieveCapa } from "@/hooks/useRetrieveCapa"
import { asUserInfo } from "@/lib/extended-types"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
    ArrowLeft,
    AlertTriangle,
    CheckCircle2,
    User,
    Calendar,
    FileText,
    ListChecks,
    Search,
    ShieldCheck,
    History
} from "lucide-react"
import { CapaOverviewTab } from "@/pages/quality/tabs/CapaOverviewTab"
import { CapaRcaTab } from "@/pages/quality/tabs/CapaRcaTab"
import { CapaTasksTab } from "@/pages/quality/tabs/CapaTasksTab"
import { CapaVerificationTab } from "@/pages/quality/tabs/CapaVerificationTab"
import { CapaApprovalTab } from "@/pages/quality/tabs/CapaApprovalTab"
import { CapaDocumentsTab } from "@/pages/quality/tabs/CapaDocumentsTab"
import { CapaHistoryTab } from "@/pages/quality/tabs/CapaHistoryTab"

// Demo data for ID 0
const DEMO_CAPA = {
    id: 0,
    capa_number: "CAPA-2024-0001",
    capa_type: "CORRECTIVE" as const,
    capa_type_display: "Corrective Action",
    severity: "MAJOR" as const,
    severity_display: "Major",
    status: "IN_PROGRESS" as const,
    status_display: "In Progress",
    problem_statement: "During routine quality inspection of Order #12345, multiple units from Batch B2024-089 showed dimensional variations outside acceptable tolerances. Specifically, the outer diameter measurements ranged from 25.8mm to 26.4mm against the specification of 26.0mm ± 0.1mm.\n\nThis affects approximately 15% of the batch (47 units out of 312 inspected). The non-conforming units have been quarantined pending disposition.",
    immediate_action: "1. Quarantined all affected units from Batch B2024-089\n2. Halted production on Machine #3 pending investigation\n3. Notified customer about potential delay\n4. Implemented 100% inspection for current production",
    initiated_by: 1,
    initiated_by_info: { username: "jsmith", email: "jsmith@company.com" },
    initiated_date: "2024-11-15",
    assigned_to: 2,
    assigned_to_info: { username: "mwilliams", email: "mwilliams@company.com" },
    due_date: "2024-12-15",
    completed_date: null,
    verified_by: null,
    verified_by_info: {},
    approval_required: true,
    approval_status: "PENDING" as const,
    approval_status_display: "Pending",
    approved_by: null,
    approved_by_info: {},
    approved_at: null,
    allow_self_verification: false,
    part: 1234,
    step: 5,
    work_order: 12345,
    quality_reports: [101, 102],
    dispositions: [201],
    completion_percentage: 65,
    is_overdue: false,
    blocking_items: [],
    created_at: "2024-11-15T10:30:00Z",
    updated_at: "2024-11-28T14:22:00Z",
    archived: false,
    tasks: [
        {
            id: 1,
            task_number: "TASK-001",
            capa: 0,
            capa_info: {},
            task_type: "CONTAINMENT" as const,
            task_type_display: "Containment",
            description: "Quarantine all units from Batch B2024-089 and perform 100% inspection",
            assigned_to: 3,
            assigned_to_info: { username: "tjohnson", email: "tjohnson@company.com" },
            assignees: [],
            completion_mode: "SINGLE_OWNER" as const,
            completion_mode_display: "Single Owner",
            due_date: "2024-11-16",
            status: "COMPLETED" as const,
            status_display: "Completed",
            completed_by: 3,
            completed_by_info: { username: "tjohnson" },
            completed_date: "2024-11-16",
            completion_notes: "All 312 units inspected. 47 non-conforming units identified and segregated.",
            is_overdue: false,
            created_at: "2024-11-15T11:00:00Z",
            updated_at: "2024-11-16T16:30:00Z",
            archived: false,
        },
        {
            id: 2,
            task_number: "TASK-002",
            capa: 0,
            capa_info: {},
            task_type: "CORRECTIVE" as const,
            task_type_display: "Corrective Action",
            description: "Recalibrate Machine #3 and verify dimensional accuracy",
            assigned_to: 4,
            assigned_to_info: { username: "rgarcia", email: "rgarcia@company.com" },
            assignees: [],
            completion_mode: "SINGLE_OWNER" as const,
            completion_mode_display: "Single Owner",
            due_date: "2024-11-22",
            status: "COMPLETED" as const,
            status_display: "Completed",
            completed_by: 4,
            completed_by_info: { username: "rgarcia" },
            completed_date: "2024-11-21",
            completion_notes: "Machine recalibrated. Test runs show all dimensions within spec.",
            is_overdue: false,
            created_at: "2024-11-15T11:15:00Z",
            updated_at: "2024-11-21T14:00:00Z",
            archived: false,
        },
        {
            id: 3,
            task_number: "TASK-003",
            capa: 0,
            capa_info: {},
            task_type: "CORRECTIVE" as const,
            task_type_display: "Corrective Action",
            description: "Update preventive maintenance schedule for Machine #3",
            assigned_to: 2,
            assigned_to_info: { username: "mwilliams", email: "mwilliams@company.com" },
            assignees: [],
            completion_mode: "SINGLE_OWNER" as const,
            completion_mode_display: "Single Owner",
            due_date: "2024-12-01",
            status: "IN_PROGRESS" as const,
            status_display: "In Progress",
            completed_by: null,
            completed_by_info: {},
            completed_date: null,
            completion_notes: null,
            is_overdue: false,
            created_at: "2024-11-17T09:00:00Z",
            updated_at: "2024-11-28T10:00:00Z",
            archived: false,
        },
        {
            id: 4,
            task_number: "TASK-004",
            capa: 0,
            capa_info: {},
            task_type: "PREVENTIVE" as const,
            task_type_display: "Preventive Action",
            description: "Implement SPC monitoring for critical dimensions on all CNC machines",
            assigned_to: 2,
            assigned_to_info: { username: "mwilliams", email: "mwilliams@company.com" },
            assignees: [],
            completion_mode: "SINGLE_OWNER" as const,
            completion_mode_display: "Single Owner",
            due_date: "2024-12-10",
            status: "NOT_STARTED" as const,
            status_display: "Not Started",
            completed_by: null,
            completed_by_info: {},
            completed_date: null,
            completion_notes: null,
            is_overdue: false,
            created_at: "2024-11-20T11:00:00Z",
            updated_at: "2024-11-20T11:00:00Z",
            archived: false,
        },
    ],
    rca_records: [
        {
            id: 1,
            capa: 0,
            capa_info: {},
            rca_method: "FIVE_WHYS" as const,
            rca_method_display: "5 Whys",
            problem_description: "Parts from Machine #3 showing dimensional variations outside tolerance (25.8-26.4mm vs 26.0±0.1mm spec)",
            root_cause_summary: "Root cause identified as worn spindle bearings in Machine #3, combined with inadequate preventive maintenance frequency.",
            conducted_by: 2,
            conducted_by_info: { username: "mwilliams" },
            conducted_date: "2024-11-18",
            rca_review_status: "COMPLETED" as const,
            rca_review_status_display: "Completed",
            root_cause_verification_status: "VERIFIED" as const,
            root_cause_verification_status_display: "Verified",
            root_cause_verified_at: "2024-11-19T10:00:00Z",
            root_cause_verified_by: 5,
            root_cause_verified_by_info: { username: "quality_mgr" },
            self_verified: false,
            quality_reports: [101],
            dispositions: [],
            five_whys: {
                id: 1,
                rca_record: 1,
                why1: "Why are parts out of tolerance? - Machine #3 is producing parts with excessive dimensional variation.",
                why2: "Why is Machine #3 producing variation? - The spindle is not maintaining consistent position during cutting.",
                why3: "Why is the spindle inconsistent? - The spindle bearings are worn beyond acceptable limits.",
                why4: "Why are the bearings worn? - The bearings exceeded their service life without replacement.",
                why5: "Why weren't they replaced? - The preventive maintenance schedule was set at 12-month intervals, but these bearings require 6-month replacement under our production volume.",
            },
            fishbone: null,
            root_causes: [
                {
                    id: 1,
                    rca_record: 1,
                    rca_record_info: {},
                    description: "Spindle bearings worn beyond service limits",
                    category: "MACHINE" as const,
                    category_display: "Machine",
                    role: "PRIMARY" as const,
                    role_display: "Primary",
                    sequence: 1,
                    created_at: "2024-11-18T14:00:00Z",
                    updated_at: "2024-11-18T14:00:00Z",
                    archived: false,
                },
                {
                    id: 2,
                    rca_record: 1,
                    rca_record_info: {},
                    description: "Inadequate preventive maintenance frequency for high-volume production",
                    category: "METHOD" as const,
                    category_display: "Method",
                    role: "CONTRIBUTING" as const,
                    role_display: "Contributing",
                    sequence: 2,
                    created_at: "2024-11-18T14:05:00Z",
                    updated_at: "2024-11-18T14:05:00Z",
                    archived: false,
                },
            ],
            created_at: "2024-11-18T10:00:00Z",
            updated_at: "2024-11-19T10:00:00Z",
            archived: false,
        },
    ],
    verifications: [
        {
            id: 1,
            capa: 0,
            capa_info: {},
            verification_method: "Production run verification with 100% dimensional inspection",
            verification_criteria: "30 consecutive production runs with all dimensions within specification (26.0mm ± 0.1mm). Zero non-conformances over 2-week monitoring period.",
            verification_date: null,
            verified_by: null,
            verified_by_info: {},
            effectiveness_result: undefined,
            effectiveness_result_display: "Pending",
            effectiveness_decided_at: null,
            verification_notes: null,
            self_verified: false,
            created_at: "2024-11-22T09:00:00Z",
            updated_at: "2024-11-22T09:00:00Z",
            archived: false,
        },
    ],
};

export function CapaDetailPage() {
    const { id } = useParams({ from: "/quality/capas/$id" })
    const capaId = id
    const isDemo = capaId === 0

    const { data: fetchedCapa, isLoading, error } = useRetrieveCapa(capaId)

    // Use demo data for ID 0, otherwise use fetched data
    const capa = isDemo ? DEMO_CAPA : fetchedCapa

    if (!isDemo && isLoading) {
        return (
            <div className="container mx-auto p-6 space-y-6">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-64 w-full" />
            </div>
        )
    }

    if (!isDemo && (error || !capa)) {
        return (
            <div className="container mx-auto p-6">
                <Card className="border-destructive">
                    <CardHeader>
                        <CardTitle className="text-destructive">Error Loading CAPA</CardTitle>
                        <CardDescription>
                            Unable to load CAPA #{id}. It may not exist or you may not have permission to view it.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button asChild variant="outline">
                            <Link to="/quality/capas">
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back to CAPAs
                            </Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    if (!capa) {
        return null
    }

    const assignedToInfo = asUserInfo(capa.assigned_to_info)
    const initiatedByInfo = asUserInfo(capa.initiated_by_info)

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <Button asChild variant="ghost" size="sm">
                            <Link to="/quality/capas">
                                <ArrowLeft className="h-4 w-4 mr-1" />
                                Back
                            </Link>
                        </Button>
                    </div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <span className="font-mono">{capa?.capa_number}</span>
                        <StatusBadge status={capa?.status} label={capa?.status_display} />
                        <StatusBadge status={capa?.severity} label={capa?.severity_display} />
                        {capa?.is_overdue && (
                            <Badge variant="destructive" className="gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Overdue
                            </Badge>
                        )}
                    </h1>
                    <p className="text-muted-foreground">{capa?.capa_type_display}</p>
                </div>

            </div>

            {/* Summary Card */}
            <Card>
                <CardContent className="pt-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <User className="h-4 w-4" />
                                Assigned To
                            </div>
                            <p className="font-medium">
                                {assignedToInfo?.full_name || assignedToInfo?.username || "Unassigned"}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <User className="h-4 w-4" />
                                Initiated By
                            </div>
                            <p className="font-medium">
                                {initiatedByInfo?.full_name || initiatedByInfo?.username || "Unknown"}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Calendar className="h-4 w-4" />
                                Due Date
                            </div>
                            <p className={`font-medium ${capa?.is_overdue ? "text-destructive" : ""}`}>
                                {capa?.due_date
                                    ? new Date(capa.due_date).toLocaleDateString()
                                    : "Not set"}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <CheckCircle2 className="h-4 w-4" />
                                Progress
                            </div>
                            <div className="flex items-center gap-2">
                                <Progress value={capa?.completion_percentage ?? 0} className="h-2 flex-1" />
                                <span className="font-medium text-sm">{capa?.completion_percentage ?? 0}%</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Tabs */}
            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList className="grid w-full grid-cols-7">
                    <TabsTrigger value="overview" className="gap-2">
                        <FileText className="h-4 w-4" />
                        Overview
                    </TabsTrigger>
                    <TabsTrigger value="rca" className="gap-2">
                        <Search className="h-4 w-4" />
                        Root Cause
                    </TabsTrigger>
                    <TabsTrigger value="tasks" className="gap-2">
                        <ListChecks className="h-4 w-4" />
                        Tasks
                        {capa?.tasks && capa.tasks.length > 0 && (
                            <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                                {capa.tasks.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="verification" className="gap-2">
                        <ShieldCheck className="h-4 w-4" />
                        Verification
                    </TabsTrigger>
                    <TabsTrigger value="approval" className="gap-2">
                        <CheckCircle2 className="h-4 w-4" />
                        Approval
                        {capa?.approval_status === 'PENDING' && (
                            <Badge variant="secondary" className="ml-1 h-5 px-1.5 bg-yellow-100 text-yellow-800">
                                !
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="documents" className="gap-2">
                        <FileText className="h-4 w-4" />
                        Documents
                    </TabsTrigger>
                    <TabsTrigger value="history" className="gap-2">
                        <History className="h-4 w-4" />
                        History
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview">
                    <CapaOverviewTab capa={capa} />
                </TabsContent>

                <TabsContent value="rca">
                    <CapaRcaTab capa={capa} />
                </TabsContent>

                <TabsContent value="tasks">
                    <CapaTasksTab capa={capa} />
                </TabsContent>

                <TabsContent value="verification">
                    <CapaVerificationTab capa={capa} />
                </TabsContent>

                <TabsContent value="approval">
                    <CapaApprovalTab capa={capa} />
                </TabsContent>

                <TabsContent value="documents">
                    <CapaDocumentsTab capa={capa} />
                </TabsContent>

                <TabsContent value="history">
                    <CapaHistoryTab capa={capa} />
                </TabsContent>
            </Tabs>
        </div>
    )
}