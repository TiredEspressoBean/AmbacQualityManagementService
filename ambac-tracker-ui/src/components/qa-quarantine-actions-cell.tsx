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
import { PartQualityForm } from "@/components/part-quality-form"
import { useUpdatePart } from "@/hooks/useUpdatePart"
import { toast } from "sonner"

type PartType = z.infer<typeof schemas.Parts>

interface PartActionsCellProps {
    part: PartType
    onPass?: (part: PartType) => void
    onError?: (part: PartType) => void
    onArchive?: (part: PartType) => void
}

export function QaQuarantineActionsCell({ part, onError }: PartActionsCellProps) {
    const [sheet, setSheet] = useState<"quality" | null>(null)
    const updatePart = useUpdatePart()

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
                <Button size="sm" onClick={() => setSheet("quality")}>
                    Quality Report
                </Button>
                <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleStatusChange("SCRAPPED")}
                >
                    Mark Scrap
                </Button>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleStatusChange("REWORK_NEEDED")}
                >
                    Mark Rework
                </Button>
            </div>

            <Sheet open={sheet !== null} onOpenChange={(open) => !open && setSheet(null)}>
                <SheetContent side="right" className="p-0 w-full">
                    <form className="flex h-full w-full flex-col">
                        <SheetHeader className="flex-none border-b p-6 text-left">
                            <SheetTitle>Submit Quality Report</SheetTitle>
                        </SheetHeader>

                        <div className="flex-1 overflow-y-auto p-6">
                            <PartQualityForm
                                part={part}
                                onClose={() => {
                                    onError?.(part)
                                    handleClose()
                                }}
                            />
                        </div>
                    </form>
                </SheetContent>
            </Sheet>
        </>
    )
}
