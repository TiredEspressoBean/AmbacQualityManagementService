import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/status-badge"
import { Link } from "@tanstack/react-router"
import { useRetrieveQualityReportsBatch } from "@/hooks/useRetrieveQualityReportsBatch"
import { useRetrieveDispositionsBatch } from "@/hooks/useRetrieveDispositionsBatch"
import { AlertTriangle } from "lucide-react"
import { asUserInfo } from "@/lib/extended-types"

type CapaOverviewTabProps = {
    capa: any
}

export function CapaOverviewTab({ capa }: CapaOverviewTabProps) {
    const qualityReportIds = capa?.quality_reports || []
    const dispositionIds = capa?.dispositions || []

    const { data: qualityReportsData } = useRetrieveQualityReportsBatch(qualityReportIds)
    const { data: dispositionsData } = useRetrieveDispositionsBatch(dispositionIds)

    if (!capa) {
        return null
    }

    const approvedByInfo = asUserInfo(capa.approved_by_info)

    return (
        <div className="grid gap-4 md:grid-cols-2">
            <Card className="md:col-span-2">
                <CardHeader>
                    <CardTitle>Problem Statement</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="whitespace-pre-wrap">{capa.problem_statement}</p>
                </CardContent>
            </Card>

            {capa.immediate_action && (
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>Immediate/Containment Action</CardTitle>
                        <CardDescription>Action taken immediately to contain the issue</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="whitespace-pre-wrap">{capa.immediate_action}</p>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground">Type</span>
                            <p className="font-medium">{capa.capa_type_display}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Severity</span>
                            <p className="font-medium">{capa.severity_display}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Initiated Date</span>
                            <p className="font-medium">
                                {capa?.initiated_date ? new Date(capa.initiated_date).toLocaleDateString() : "—"}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Due Date</span>
                            <p className="font-medium">
                                {capa.due_date
                                    ? new Date(capa.due_date).toLocaleDateString()
                                    : "Not set"}
                            </p>
                        </div>
                        {capa?.completed_date && (
                            <div>
                                <span className="text-muted-foreground">Completed Date</span>
                                <p className="font-medium">
                                    {new Date(capa.completed_date).toLocaleDateString()}
                                </p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Approval Status</CardTitle>
                        {capa.approval_status && (
                            <StatusBadge status={capa.approval_status} />
                        )}
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Warning for pending approval on Critical/Major */}
                    {capa?.approval_status === 'PENDING' && (capa?.severity === 'CRITICAL' || capa?.severity === 'MAJOR') && (
                        <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
                            <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                            <div className="text-sm">
                                <p className="font-medium text-yellow-800">Approval Required</p>
                                <p className="text-yellow-700">
                                    This {capa?.severity_display} severity CAPA requires management approval before work can begin.
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground">Approval Required</span>
                            <p className="font-medium">{capa?.approval_required ? "Yes" : "No"}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Status</span>
                            <p className="font-medium">{capa?.approval_status_display || "Not Required"}</p>
                        </div>
                        {approvedByInfo?.username && (
                            <>
                                <div>
                                    <span className="text-muted-foreground">
                                        {capa?.approval_status === 'REJECTED' ? 'Rejected By' : 'Approved By'}
                                    </span>
                                    <p className="font-medium">
                                        {approvedByInfo.full_name || approvedByInfo.username}
                                    </p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">
                                        {capa?.approval_status === 'REJECTED' ? 'Rejected At' : 'Approved At'}
                                    </span>
                                    <p className="font-medium">
                                        {capa?.approved_at
                                            ? new Date(capa.approved_at).toLocaleDateString()
                                            : "—"}
                                    </p>
                                </div>
                            </>
                        )}
                    </div>

                    {/* Action hint - direct user to Approval tab */}
                    {capa?.approval_status === 'PENDING' && (
                        <p className="text-sm text-muted-foreground">
                            View the <span className="font-medium">Approval</span> tab to submit or review approval responses.
                        </p>
                    )}
                </CardContent>
            </Card>

            {(capa?.part || capa?.step || capa?.work_order) && (
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>Related Items</CardTitle>
                        <CardDescription>Parts, processes, or work orders associated with this CAPA</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                            {capa?.part && (
                                <div>
                                    <span className="text-muted-foreground">Part</span>
                                    <p className="font-medium">Part #{capa.part}</p>
                                </div>
                            )}
                            {capa?.step && (
                                <div>
                                    <span className="text-muted-foreground">Process Step</span>
                                    <p className="font-medium">Step #{capa.step}</p>
                                </div>
                            )}
                            {capa?.work_order && (
                                <div>
                                    <span className="text-muted-foreground">Work Order</span>
                                    <p className="font-medium">WO #{capa.work_order}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {qualityReportIds.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Linked Quality Reports</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-1">
                            {(qualityReportsData || qualityReportIds).map((report: { id?: string; report_number?: string } | string) => {
                                const id = report?.id || report
                                const name = report?.report_number || `NCR-${id}`
                                return (
                                    <li key={id}>
                                        <Link
                                            to="/quality/reports/$id"
                                            params={{ id: String(id) }}
                                            className="text-primary hover:underline"
                                        >
                                            {name}
                                        </Link>
                                    </li>
                                )
                            })}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {dispositionIds.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Linked Dispositions</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-1">
                            {(dispositionsData || dispositionIds).map((disp: any) => {
                                const id = disp?.id || disp
                                const name = disp?.disposition_number || `QD-${id}`
                                return (
                                    <li key={id}>
                                        <Link
                                            to="/quality/dispositions/$id"
                                            params={{ id: String(id) }}
                                            className="text-primary hover:underline"
                                        >
                                            {name}
                                        </Link>
                                    </li>
                                )
                            })}
                        </ul>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
