import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import {
    User,
    Calendar,
    FileType,
    Link as LinkIcon,
    Bot,
    Download,
    Eye,
    Unlink,
    Plus,
} from "lucide-react"
import { useDetachDocument } from "@/hooks/useDetachDocument"
import { usePermissionSet } from "@/hooks/useMyPermissions"
import { AttachDocumentDialog } from "@/components/documents/AttachDocumentDialog"

type DocumentOverviewTabProps = {
    document: any
}

/** A secondary association surfaced from `Documents.links` (loosely typed by
 *  the generated client). */
type LinkEntry = {
    id: string
    content_type: number
    model: string | null
    object_id: string
    target_str: string | null
}

/** Map a raw Django model name to a human-friendly label. Falls back to
 *  title-casing the raw name so unmapped types are still legible. */
const MODEL_LABELS: Record<string, string> = {
    orders: "Order",
    parts: "Part",
    parttypes: "Part Type",
    workorder: "Work Order",
    steps: "Step",
    processes: "Process",
    equipments: "Equipment",
    companies: "Company",
    qualityreports: "Quality Report",
    quarantinedisposition: "Disposition",
    capa: "CAPA",
    threedmodel: "3D Model",
    materiallot: "Material Lot",
    documents: "Document",
}

function friendlyModelLabel(model: string | null | undefined): string {
    if (!model) return "Object"
    const key = model.toLowerCase()
    if (MODEL_LABELS[key]) return MODEL_LABELS[key]
    // Fallback: split snake/camel boundaries and title-case.
    return key
        .replace(/[_-]+/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function DocumentOverviewTab({ document }: DocumentOverviewTabProps) {
    const isImage = document.is_image
    const isPdf = document.file_name?.toLowerCase().endsWith('.pdf')

    const links: LinkEntry[] = document.links ?? []
    const { has } = usePermissionSet()
    const canDetach = has("delete_documentlink")
    const canAttach = has("add_documentlink")
    const detach = useDetachDocument()
    const [attachOpen, setAttachOpen] = useState(false)

    // Build preview URL
    const fileUrl = document.file ?
        (document.file.startsWith('http') ? document.file : `/media/${document.file}`) :
        null

    return (
        <div className="grid gap-4 md:grid-cols-2">
            {/* File Preview Card */}
            <Card className="md:col-span-2">
                <CardHeader>
                    <CardTitle>File Preview</CardTitle>
                </CardHeader>
                <CardContent>
                    {isImage && fileUrl ? (
                        <div className="flex justify-center">
                            <img
                                src={fileUrl}
                                alt={document.file_name}
                                className="max-h-[500px] object-contain rounded-lg border"
                            />
                        </div>
                    ) : isPdf && fileUrl ? (
                        <div className="border rounded-lg overflow-hidden">
                            <iframe
                                src={fileUrl}
                                className="w-full h-[600px]"
                                title={document.file_name}
                            />
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <FileType className="h-16 w-16 mb-4" />
                            <p className="text-lg font-medium">{document.file_name}</p>
                            <p className="text-sm mb-4">Preview not available for this file type</p>
                            <Button
                                variant="outline"
                                onClick={() => window.open(`/api/Documents/${document.id}/download/`, '_blank')}
                            >
                                <Download className="h-4 w-4 mr-2" />
                                Download to View
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Metadata Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Document Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1">
                                <User className="h-4 w-4" />
                                Uploaded By
                            </span>
                            <p className="font-medium">
                                {document.uploaded_by_name || document.uploaded_by || "Unknown"}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                Upload Date
                            </span>
                            <p className="font-medium">
                                {document.upload_date
                                    ? new Date(document.upload_date).toLocaleDateString()
                                    : "Unknown"}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Classification</span>
                            <p className="font-medium capitalize">{document.classification}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Version</span>
                            <p className="font-medium">{document.version || 1}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Status</span>
                            <p className="font-medium">{document.status_display || document.status}</p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1">
                                <Bot className="h-4 w-4" />
                                AI Readable
                            </span>
                            <p className="font-medium">{document.ai_readable ? "Yes" : "No"}</p>
                        </div>
                    </div>

                    {document.ID_prefix && (
                        <div>
                            <span className="text-muted-foreground text-sm">Document ID</span>
                            <p className="font-mono font-medium">{document.ID_prefix}</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Linked Object Card */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <LinkIcon className="h-5 w-5" />
                        Linked To
                    </CardTitle>
                    <CardDescription>
                        The object this document is attached to
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {document.content_type && document.object_id ? (
                        <div className="space-y-2">
                            <div className="p-3 border rounded-lg">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">
                                            {friendlyModelLabel(document.content_type_info?.model)}
                                        </p>
                                        <p className="font-medium">
                                            {document.content_object_display || `#${document.object_id}`}
                                        </p>
                                    </div>
                                    <Button variant="ghost" size="sm">
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">
                            This document is not linked to any specific object.
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* Secondary associations (DocumentLink) — additional entities this
                document is linked to beyond its primary owner. */}
            {(links.length > 0 || canAttach) && (
                <Card>
                    <CardHeader>
                        <div className="flex items-start justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <LinkIcon className="h-5 w-5" />
                                    Also Linked To
                                </CardTitle>
                                <CardDescription>
                                    Additional entities this document is associated with
                                </CardDescription>
                            </div>
                            {canAttach && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setAttachOpen(true)}
                                >
                                    <Plus className="h-4 w-4 mr-1" />
                                    Attach
                                </Button>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {links.length === 0 ? (
                            <p className="text-sm text-muted-foreground">
                                No additional links.
                            </p>
                        ) : (
                        <div className="space-y-2">
                            {links.map((link) => {
                                const isDetaching =
                                    detach.isPending &&
                                    detach.variables?.objectId === link.object_id &&
                                    detach.variables?.contentType === link.content_type
                                return (
                                    <div key={link.id} className="p-3 border rounded-lg">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm text-muted-foreground">
                                                    {friendlyModelLabel(link.model)}
                                                </p>
                                                <p className="font-medium">
                                                    {link.target_str || `#${link.object_id}`}
                                                </p>
                                            </div>
                                            {canDetach && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    disabled={isDetaching}
                                                    onClick={() =>
                                                        detach.mutate({
                                                            id: document.id,
                                                            contentType: link.content_type,
                                                            objectId: link.object_id,
                                                        })
                                                    }
                                                    title="Remove this association"
                                                >
                                                    <Unlink className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Approval Info (if approved) */}
            {document.approved_by && (
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>Approval Information</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                                <span className="text-muted-foreground">Approved By</span>
                                <p className="font-medium">
                                    {document.approved_by_name || document.approved_by}
                                </p>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Approved At</span>
                                <p className="font-medium">
                                    {document.approved_at
                                        ? new Date(document.approved_at).toLocaleString()
                                        : "—"}
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {canAttach && (
                <AttachDocumentDialog
                    documentId={document.id}
                    open={attachOpen}
                    onOpenChange={setAttachOpen}
                />
            )}
        </div>
    )
}
