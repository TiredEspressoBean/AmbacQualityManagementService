/**
 * Properties panel that watches the editor's current selection and renders
 * the matching node's edit form. Pattern matches what most no-code DWI / form
 * builders use (Tulip, FactoryLogix, Typeform) — the selected node drives a
 * side panel rather than a click-popover.
 *
 * Forms are reused from each node module — they accept the same
 * `{ node, updateAttributes }` shape they get inside NodeViewProps, so this
 * panel just builds an adapter that routes `updateAttributes` through the
 * editor's `updateAttributes(typeName, partial)` command.
 */
import { useEffect, useState } from "react";
import type { Editor } from "@tiptap/core";
import type { NodeViewProps } from "@tiptap/react";
import { NodeSelection } from "@tiptap/pm/state";

import { MeasurementSpecEditForm } from "./nodes/MeasurementSpec";
import { MediaEditForm } from "./nodes/Media";
import { DocumentLinkEditForm } from "./nodes/DocumentLink";
import { AttestationCheckpointEditForm } from "./nodes/AttestationCheckpoint";
import { MeasurementInputEditForm } from "./nodes/MeasurementInput";
import { TextInputEditForm } from "./nodes/TextInput";
import { ChoiceInputEditForm } from "./nodes/ChoiceInput";
import { ScanInputEditForm } from "./nodes/ScanInput";
import { TimerEditForm } from "./nodes/Timer";
import { ComputedValueEditForm } from "./nodes/ComputedValue";
import { FileLikeEditForm } from "./shared/FileLikeCapture";
import { QualityStatusFieldEditForm } from "./nodes/QualityStatusField";
import { EquipmentRolesFieldEditForm } from "./nodes/EquipmentRolesField";
import { PersonnelRolesFieldEditForm } from "./nodes/PersonnelRolesField";
import { InspectionSignaturesEditForm } from "./nodes/InspectionSignatures";
import { ErrorTypesFieldEditForm } from "./nodes/ErrorTypesField";
import { PartAnnotationEditForm } from "./nodes/PartAnnotation";
import { HarvestedComponentCaptureEditForm } from "./nodes/HarvestedComponentCapture";

const FORMS: Record<string, React.ComponentType<NodeViewProps>> = {
    measurementSpec: MeasurementSpecEditForm,
    media: MediaEditForm,
    documentLink: DocumentLinkEditForm,
    attestationCheckpoint: AttestationCheckpointEditForm,
    measurementInput: MeasurementInputEditForm,
    textInput: TextInputEditForm,
    choiceInput: ChoiceInputEditForm,
    scanInput: ScanInputEditForm,
    timer: TimerEditForm,
    computedValue: ComputedValueEditForm,
    photoCapture: FileLikeEditForm,
    fileCapture: FileLikeEditForm,
    qualityStatusField: QualityStatusFieldEditForm,
    equipmentRolesField: EquipmentRolesFieldEditForm,
    personnelRolesField: PersonnelRolesFieldEditForm,
    inspectionSignatures: InspectionSignaturesEditForm,
    errorTypesField: ErrorTypesFieldEditForm,
    partAnnotation: PartAnnotationEditForm,
    harvestedComponentCapture: HarvestedComponentCaptureEditForm,
};

const NODE_LABELS: Record<string, string> = {
    measurementSpec: "Measurement spec",
    media: "Media",
    documentLink: "Document link",
    attestationCheckpoint: "Attestation",
    measurementInput: "Measurement input",
    textInput: "Text input",
    choiceInput: "Choice input",
    scanInput: "Scan input",
    timer: "Timer",
    computedValue: "Computed value",
    photoCapture: "Photo capture",
    fileCapture: "File capture",
    qualityStatusField: "Quality status",
    equipmentRolesField: "Equipment + roles",
    personnelRolesField: "Personnel + roles",
    inspectionSignatures: "Inspection signatures",
    errorTypesField: "Defect findings",
    partAnnotation: "Part annotation (3D)",
    harvestedComponentCapture: "Harvested components (teardown)",
};

export function NodePropertiesPanel({ editor }: { editor: Editor | null }) {
    // Force re-render on every editor selection / content change so the panel
    // reflects the current node's attrs.
    const [, force] = useState(0);
    useEffect(() => {
        if (!editor) return;
        const f = () => force((t) => t + 1);
        editor.on("selectionUpdate", f);
        editor.on("update", f);
        return () => {
            editor.off("selectionUpdate", f);
            editor.off("update", f);
        };
    }, [editor]);

    if (!editor) {
        return <Placeholder>Loading editor…</Placeholder>;
    }

    const sel = editor.state.selection;
    if (!(sel instanceof NodeSelection)) {
        return (
            <Placeholder>
                Click a custom node (measurement, attestation, timer, …) to edit
                its properties here.
            </Placeholder>
        );
    }

    const node = sel.node;
    const typeName = node.type.name;
    const Form = FORMS[typeName];
    if (!Form) {
        return (
            <Placeholder>
                <code className="font-mono text-[11px]">{typeName}</code> has no
                editable properties.
            </Placeholder>
        );
    }

    const adapter = {
        node,
        updateAttributes: (partial: Record<string, unknown>) => {
            // Critical: do NOT call `.focus()` in this chain. The panel
            // input is what currently has focus — re-focusing the editor
            // mid-typing would yank focus back to ProseMirror, and with the
            // atom node selected, the next keystroke replaces the node.
            // We just update attributes; selection stays where it is.
            editor.chain().updateAttributes(typeName, partial).run();
        },
    } as unknown as NodeViewProps;

    return (
        // Isolation wrapper:
        //  - `draggable={false}` + `onDragStart` stopPropagation breaks
        //    inheritance from the SubstepRow's drag-to-reorder handler, so
        //    selecting / dragging text inside a panel input doesn't pick
        //    up the whole row.
        //  - `onKeyDown` stopPropagation prevents Backspace / Delete from
        //    bubbling to the ProseMirror editor, which would otherwise
        //    treat them as "delete the selected atom node" — clearing a
        //    label in the panel was nuking the node.
        //  - `onMouseDown` stopPropagation keeps Tiptap's selection from
        //    flickering when the operator clicks deeper into the form.
        <div
            className="space-y-3 p-3"
            draggable={false}
            onDragStart={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
        >
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {NODE_LABELS[typeName] ?? typeName}
            </div>
            <Form {...adapter} />
        </div>
    );
}

function Placeholder({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-full items-center justify-center p-6 text-center text-xs text-muted-foreground">
            {children}
        </div>
    );
}
