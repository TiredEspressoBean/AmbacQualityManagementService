import { Button } from "@/components/ui/button"
import { schemas } from "@/lib/api/generated"
import { z } from "zod"
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions"
import { Link } from "@tanstack/react-router"
import { ExternalLink, Loader2 } from "lucide-react"

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
    const { data: dispositionsData, isLoading, isError } = useRetrieveQuarantineDispositions({
        part: part.id
    })

    // Find the first non-closed disposition (auto-created when QR fails)
    const activeDisposition = dispositionsData?.results?.find(d => d.current_state !== "CLOSED")

    // Wait for the lookup before offering an action. Rendering the "create"
    // button while the query is still in flight (data === undefined) would let
    // someone open /dispositions/create for a part that ALREADY has an open
    // disposition — a duplicate NCR. Show a spinner until we actually know.
    if (isLoading) {
        return (
            <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" className="gap-2" disabled>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Checking…
                </Button>
            </div>
        )
    }

    // On error we also can't safely offer "create" (we don't know if one
    // exists) — surface a disabled state rather than risk a duplicate.
    if (isError) {
        return (
            <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" disabled>
                    Unavailable
                </Button>
            </div>
        )
    }

    // Lookup resolved: link to edit if a disposition exists, else create.
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
