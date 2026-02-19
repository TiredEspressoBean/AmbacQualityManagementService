import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Download, CheckCircle2, History, Loader2, ExternalLink } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { useDocumentVersionHistory } from "@/hooks/useDocumentVersionHistory"

type DocumentVersionsTabProps = {
    document: any
}

export function DocumentVersionsTab({ document }: DocumentVersionsTabProps) {
    const { data: versionHistory, isLoading } = useDocumentVersionHistory(document.id)

    // Use fetched version history if available, otherwise fall back to current document
    const versions = versionHistory && Array.isArray(versionHistory) && versionHistory.length > 0
        ? versionHistory
        : [{
            id: document.id,
            version: document.version || 1,
            file_name: document.file_name,
            uploaded_by_info: document.uploaded_by_info,
            upload_date: document.upload_date,
            is_current_version: document.is_current_version !== false,
            status: document.status,
            status_display: document.status_display,
            change_justification: document.change_justification,
        }]

    // Sort versions in descending order (newest first)
    const sortedVersions = [...versions].sort((a: any, b: any) => (b.version || 1) - (a.version || 1))

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <History className="h-5 w-5" />
                                Version History
                            </CardTitle>
                            <CardDescription>
                                Track changes and access previous versions of this document
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin" />
                            <span className="ml-2">Loading version history...</span>
                        </div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Version</TableHead>
                                        <TableHead>File Name</TableHead>
                                        <TableHead>Uploaded By</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Change Notes</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {sortedVersions.map((ver: { id: string; version?: number; is_current_version?: boolean; [key: string]: any }) => (
                                        <TableRow key={ver.id} className={ver.id === document.id ? "bg-muted/50" : ""}>
                                            <TableCell>
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono font-medium">v{ver.version || 1}</span>
                                                    {ver.is_current_version && (
                                                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                                            <CheckCircle2 className="h-3 w-3 mr-1" />
                                                            Current
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>{ver.file_name}</TableCell>
                                            <TableCell>
                                                {ver.uploaded_by_info?.full_name || ver.uploaded_by_info?.email || "Unknown"}
                                            </TableCell>
                                            <TableCell>
                                                {ver.upload_date
                                                    ? new Date(ver.upload_date).toLocaleDateString()
                                                    : "—"}
                                            </TableCell>
                                            <TableCell>
                                                <StatusBadge
                                                    status={ver.status}
                                                    label={ver.status_display || ver.status}
                                                />
                                            </TableCell>
                                            <TableCell className="max-w-[200px]">
                                                {ver.change_justification ? (
                                                    <span className="text-sm text-muted-foreground truncate block">
                                                        {ver.change_justification}
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-muted-foreground">—</span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-1">
                                                    {ver.id !== document.id && (
                                                        <Link to="/documents/$id" params={{ id: String(ver.id) }}>
                                                            <Button variant="ghost" size="sm" title="View this version">
                                                                <ExternalLink className="h-4 w-4" />
                                                            </Button>
                                                        </Link>
                                                    )}
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => window.open(`/api/Documents/${ver.id}/download/`, '_blank')}
                                                        title="Download"
                                                    >
                                                        <Download className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>

                            {sortedVersions.length === 1 && (
                                <p className="text-sm text-muted-foreground text-center py-4">
                                    This is the only version of this document.
                                </p>
                            )}
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Version comparison (placeholder for future) */}
            <Card>
                <CardHeader>
                    <CardTitle>Current Version Notes</CardTitle>
                    <CardDescription>
                        Change justification for this version
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {document.change_justification ? (
                        <p className="whitespace-pre-wrap">{document.change_justification}</p>
                    ) : (
                        <p className="text-sm text-muted-foreground">
                            {document.version === 1 || !document.version
                                ? "This is the original version."
                                : "No change notes recorded for this version."}
                        </p>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
