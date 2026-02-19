import { Button } from "@/components/ui/button"
import { schemas } from "@/lib/api/generated"
import { z } from "zod"
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions"
import { Link } from "@tanstack/react-router"
import { ExternalLink } from "lucide-react"

type PartType = z.infer<typeof schemas.Parts>

interface PartActionsCellProps {
    part: PartType
    onPass?: (part: PartType) => void
    onError?: (part: PartType) => void
    onArchive?: (part: PartType) => void
}

export function QaQuarantineActionsCell({ part }: PartActionsCellProps) {
    // Fetch dispositions for this part to find an active one
    // Note: Quarantined parts should have auto-created dispositions from QR fail signal
    const { data: dispositionsData } = useRetrieveQuarantineDispositions({
        part: part.id
    })

    // Find the first non-closed disposition (auto-created when QR fails)
    const activeDisposition = dispositionsData?.results?.find(d => d.current_state !== "CLOSED")

    // Don't show loading - render button immediately
    // If activeDisposition is found, link to edit; otherwise link to create (fallback)
    return (
        <div className="flex flex-wrap gap-2">
            {activeDisposition ? (
                <Link to="/dispositions/edit/$id" params={{ id: String(activeDisposition.id) }}>
                    <Button size="sm" className="gap-2">
                        <ExternalLink className="h-3 w-3" />
                        Edit Disposition
                    </Button>
                </Link>
            ) : (
                <Link to="/dispositions/create" search={{ partId: String(part.id) }}>
                    <Button size="sm" variant="outline" className="gap-2">
                        <ExternalLink className="h-3 w-3" />
                        Disposition
                    </Button>
                </Link>
            )}
        </div>
    )
}
