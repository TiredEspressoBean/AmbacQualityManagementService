"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Cog } from "lucide-react";
import { MachineEligibilityTable } from "@/components/scheduling/MachineEligibilityTable";

export interface StepMachinesEditorProps {
    stepId: string;
    stepName: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    readOnly?: boolean;
}

/** Flow-editor dialog for the machines that can run a step. Each change saves at once. */
export function StepMachinesEditor({ stepId, stepName, open, onOpenChange, readOnly = false }: StepMachinesEditorProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Cog className="h-5 w-5" />
                        Machines — "{stepName}"
                    </DialogTitle>
                    <DialogDescription>
                        The machines that can run this step, and how well. The scheduler only
                        places the step on machines listed here.
                    </DialogDescription>
                </DialogHeader>
                <MachineEligibilityTable owner={{ step: stepId }} readOnly={readOnly} />
            </DialogContent>
        </Dialog>
    );
}
