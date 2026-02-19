import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollText } from "lucide-react"
import AuditTrailComponent from "@/pages/detail pages/AuditTrail"

type DocumentAuditTabProps = {
    document: any
}

export function DocumentAuditTab({ document }: DocumentAuditTabProps) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <ScrollText className="h-5 w-5" />
                    Audit Trail
                </CardTitle>
                <CardDescription>
                    Complete history of changes made to this document
                </CardDescription>
            </CardHeader>
            <CardContent>
                <AuditTrailComponent
                    objectId={document.id}
                    modelType="documents"
                />
            </CardContent>
        </Card>
    )
}
