import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments"
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes"
import DocumentsSection from "@/pages/detail pages/DocumentsSection"
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader"

type CapaDocumentsTabProps = {
    capa: any
}

export function CapaDocumentsTab({ capa }: CapaDocumentsTabProps) {
    // Get content type ID for CAPA
    const { data: contentTypes, isLoading: contentTypesLoading } = useRetrieveContentTypes({})
    // contentTypes is now an array (unpaginated) or has .results if paginated
    const contentTypesList = Array.isArray(contentTypes) ? contentTypes : contentTypes?.results
    const capaContentType = contentTypesList?.find(
        (ct: any) => ct.model === "capa" && ct.app_label === "Tracker"
    )

    // Fetch documents for this CAPA
    const { data: documentsData, isLoading, error } = useRetrieveDocuments(
        {
            content_type: capaContentType?.id,
            object_id: capa?.id,
        },
        {
            enabled: !!capaContentType?.id && !!capa?.id,
        }
    )

    const documents = documentsData?.results || []

    return (
        <Card>
            <CardHeader>
                <CardTitle>Documents</CardTitle>
                <CardDescription>
                    Files and evidence attached to this CAPA
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Upload Section */}
                {contentTypesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading...</p>
                ) : capaContentType ? (
                    <DocumentUploader
                        objectId={capa?.id}
                        contentType={capaContentType.id.toString()}
                    />
                ) : (
                    <p className="text-sm text-destructive">Could not find CAPA content type</p>
                )}

                {/* Documents List */}
                <div className="border-t pt-4">
                    <DocumentsSection
                        documents={documents}
                        isLoading={isLoading}
                        error={error}
                    />
                </div>
            </CardContent>
        </Card>
    )
}
