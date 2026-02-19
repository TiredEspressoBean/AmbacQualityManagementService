import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import AuditTrailComponent from "@/pages/detail pages/AuditTrail"

type CapaHistoryTabProps = {
    capa: any
}

export function CapaHistoryTab({ capa }: CapaHistoryTabProps) {
    if (!capa) {
        return null
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Activity History</CardTitle>
                <CardDescription>
                    Timeline of changes and updates to this CAPA
                </CardDescription>
            </CardHeader>
            <CardContent>
                <AuditTrailComponent objectId={capa?.id} modelType="CAPA" />
            </CardContent>
        </Card>
    )
}