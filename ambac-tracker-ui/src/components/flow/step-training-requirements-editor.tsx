"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { GraduationCap } from "lucide-react";
import { TrainingRequirementsEditor } from "@/components/training/TrainingRequirementsEditor";

export interface StepTrainingRequirementsEditorProps {
    stepId: string;
    stepName: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    readOnly?: boolean;
}

/**
 * Flow-editor dialog for a step's training requirements — the competencies an
 * operator must hold to be authorized for this operation. Wraps the shared
 * TrainingRequirementsEditor scoped to the step; each add/remove persists
 * immediately (no explicit save).
 */
export function StepTrainingRequirementsEditor({
    stepId,
    stepName,
    open,
    onOpenChange,
    readOnly = false,
}: StepTrainingRequirementsEditorProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <GraduationCap className="h-5 w-5" />
                        Required Training — "{stepName}"
                    </DialogTitle>
                    <DialogDescription>
                        Competencies an operator must hold to be authorized for this operation.
                    </DialogDescription>
                </DialogHeader>
                <TrainingRequirementsEditor
                    scope={{ step: stepId }}
                    title="Required training"
                    description="Operators need these certifications (at the given level) to run this step."
                    readOnly={readOnly}
                />
            </DialogContent>
        </Dialog>
    );
}
