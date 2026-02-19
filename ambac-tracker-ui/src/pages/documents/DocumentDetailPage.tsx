import { useState } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { useRetrieveDocument } from "@/hooks/useRetrieveDocument"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import {
    ArrowLeft,
    Download,
    Edit,
    Loader2,
    FileText,
    History,
    ShieldCheck,
    ScrollText,
    FilePlus2,
} from "lucide-react"
import { DocumentOverviewTab } from "./tabs/DocumentOverviewTab"
import { DocumentVersionsTab } from "./tabs/DocumentVersionsTab"
import { DocumentApprovalTab } from "./tabs/DocumentApprovalTab"
import { DocumentAuditTab } from "./tabs/DocumentAuditTab"
import { DocumentRevisionModal } from "@/components/document-revision-modal"

export function DocumentDetailPage() {
    const { id } = useParams({ from: "/documents/$id" })
    const documentId = id
    const { data: document, isLoading, error } = useRetrieveDocument(documentId)
    const [showRevisionModal, setShowRevisionModal] = useState(false)

    // Can create revision if document is current version
    const canCreateRevision = document?.is_current_version !== false

    if (isLoading) {
        return (
            <div className="container mx-auto p-6 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        )
    }

    if (error || !document) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center py-12">
                    <h2 className="text-xl font-semibold mb-2">Document Not Found</h2>
                    <p className="text-muted-foreground mb-4">
                        The document you're looking for doesn't exist or you don't have access.
                    </p>
                    <Link to="/documents">
                        <Button variant="outline">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Documents
                        </Button>
                    </Link>
                </div>
            </div>
        )
    }

    const handleDownload = () => {
        // Open download URL in new tab
        window.open(`/api/Documents/${documentId}/download/`, '_blank')
    }

    return (
        <div className="container mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                    <Link to="/documents" className="hover:text-foreground">
                        Documents
                    </Link>
                    <span>/</span>
                    <span>{document.file_name}</span>
                </div>

                <div className="flex items-start justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <FileText className="h-8 w-8 text-muted-foreground" />
                            <h1 className="text-2xl font-bold">{document.file_name}</h1>
                        </div>
                        <div className="flex items-center gap-2">
                            {document.ID_prefix && (
                                <Badge variant="outline" className="font-mono">
                                    {document.ID_prefix}
                                </Badge>
                            )}
                            <Badge variant="outline">
                                v{document.version || 1}
                            </Badge>
                            <StatusBadge
                                status={document.status}
                                label={document.status_display || document.status}
                            />
                            <StatusBadge
                                status={document.classification?.toUpperCase()}
                                label={document.classification}
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button variant="outline" onClick={handleDownload}>
                            <Download className="h-4 w-4 mr-2" />
                            Download
                        </Button>
                        {canCreateRevision && (
                            <Button variant="outline" onClick={() => setShowRevisionModal(true)}>
                                <FilePlus2 className="h-4 w-4 mr-2" />
                                Create Revision
                            </Button>
                        )}
                        <Link to="/DocumentForm/edit/$id" params={{ id: String(documentId) }}>
                            <Button variant="outline">
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                            </Button>
                        </Link>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview" className="gap-2">
                        <FileText className="h-4 w-4" />
                        Overview
                    </TabsTrigger>
                    <TabsTrigger value="versions" className="gap-2">
                        <History className="h-4 w-4" />
                        Versions
                    </TabsTrigger>
                    <TabsTrigger value="approval" className="gap-2">
                        <ShieldCheck className="h-4 w-4" />
                        Approval
                    </TabsTrigger>
                    <TabsTrigger value="audit" className="gap-2">
                        <ScrollText className="h-4 w-4" />
                        Audit Trail
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview">
                    <DocumentOverviewTab document={document} />
                </TabsContent>

                <TabsContent value="versions">
                    <DocumentVersionsTab document={document} />
                </TabsContent>

                <TabsContent value="approval">
                    <DocumentApprovalTab document={document} />
                </TabsContent>

                <TabsContent value="audit">
                    <DocumentAuditTab document={document} />
                </TabsContent>
            </Tabs>

            {/* Revision Modal */}
            <DocumentRevisionModal
                documentId={documentId}
                documentName={document.file_name}
                isOpen={showRevisionModal}
                onClose={() => setShowRevisionModal(false)}
            />
        </div>
    )
}
