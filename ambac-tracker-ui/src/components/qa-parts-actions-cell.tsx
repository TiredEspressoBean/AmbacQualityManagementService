import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { useState } from "react";
import { schemas } from "@/lib/api/generated.ts";
import { z } from "zod";
import { PartQualityForm } from "@/components/part-quality-form.tsx";

type PartType = z.infer<typeof schemas.Parts>;

interface PartActionsCellProps {
    part: PartType;
    onPass?: (part: PartType) => void;
    onError?: (part: PartType) => void;
    onArchive?: (part: PartType) => void;
}

export function QaPartActionsCell({ part, onError }: PartActionsCellProps) {
    const [sheet, setSheet] = useState<"quality" | "archive" | null>(null);

    const handleClose = () => setSheet(null);

    return (
        <>
            <Button variant="default" size="sm" onClick={() => setSheet("quality")}>
                Quality Report
            </Button>

            <Sheet open={sheet !== null} onOpenChange={(open) => !open && setSheet(null)}>
                <SheetContent side="right" className="p-0 w-full">
                    <form className="flex h-full w-full flex-col">
                        <SheetHeader className="flex-none border-b p-6 text-left">
                            <SheetTitle>
                                {sheet === "quality" ? "Submit Quality Report" : "Archive Part"}
                            </SheetTitle>
                        </SheetHeader>

                        {/* Scrollable content area */}
                        <div className="flex-1 overflow-y-auto">
                            <div className="p-6">
                                    <PartQualityForm
                                        part={part}
                                        onClose={() => {
                                            onError?.(part);
                                            handleClose();
                                        }}
                                    />
                            </div>
                        </div>
                    </form>
                </SheetContent>
            </Sheet>
        </>
    );
}
