import { Button } from "@/components/ui/button"
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet"
import { useState } from "react"
import { schemas } from "@/lib/api/generated"
import { z } from "zod"
import PartDispositionForm from '@/components/part-disposition-form'
import { useUpdatePart } from "@/hooks/useUpdatePart"
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"

type PartType = z.infer<typeof schemas.Parts>

interface PartActionsCellProps {
    part: PartType
    onPass?: (part: PartType) => void
    onError?: (part: PartType) => void
    onArchive?: (part: PartType) => void
}

export function QaQuarantineActionsCell({ part, onError }: PartActionsCellProps) {
    const [sheet, setSheet] = useState<"disposition" | null>(null)
    const updatePart = useUpdatePart()

    const { data: dispositionsData, isLoading: dispositionsLoading } = useRetrieveQuarantineDispositions({
        queries: {
            part: part.id
        }
    }, {
        enabled: sheet === "disposition"
    })

    // Find the first non-closed disposition
    const activeDisposition = dispositionsData?.results?.find(d => d.current_state !== "CLOSED")

    console.log(dispositionsData)

    const handleStatusChange = (newStatus: "SCRAPPED" | "REWORK_NEEDED") => {
        updatePart.mutate(
            {
                id: part.id,
                data: {
                    part_status: newStatus,
                },
            },
            {
                onSuccess: () => toast.success(`Part marked as ${newStatus}`),
                onError: () => toast.error(`Failed to mark part as ${newStatus}`),
            }
        )
    }

    const handleClose = () => setSheet(null)

    return (
        <>
            <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => setSheet("disposition")}>
                    Disposition
                </Button>
            </div>

            <Sheet open={sheet !== null} onOpenChange={(open) => !open && setSheet(null)}>
                <SheetContent side="right" className="p-0 w-full">
                    <div className="flex h-full w-full flex-col">
                        <SheetHeader className="flex-none border-b p-6 text-left">
                            <SheetTitle>Submit Disposition Report</SheetTitle>
                        </SheetHeader>

                        <div className="flex-1 overflow-y-auto">
                            {dispositionsLoading ? (
                                <div className="flex h-full items-center justify-center p-6">
                                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                    <p className="text-sm text-muted-foreground">Loading disposition...</p>
                                </div>
                            ) : (
                                <PartDispositionForm
                                    part={part}
                                    disposition={activeDisposition}
                                    onClose={() => {
                                        onError?.(part);
                                        handleClose()
                                    }}
                                />
                            )}
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </>
    )
}
