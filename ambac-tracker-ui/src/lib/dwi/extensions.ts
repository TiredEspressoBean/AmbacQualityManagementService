import StarterKit from "@tiptap/starter-kit";
import { MeasurementSpec } from "@/components/dwi/nodes/MeasurementSpec";
import { Callout } from "@/components/dwi/nodes/Callout";
import { Media } from "@/components/dwi/nodes/Media";
import { AttestationCheckpoint } from "@/components/dwi/nodes/AttestationCheckpoint";
import { MeasurementInput } from "@/components/dwi/nodes/MeasurementInput";
import { TextInput } from "@/components/dwi/nodes/TextInput";
import { ChoiceInput } from "@/components/dwi/nodes/ChoiceInput";
import { PhotoCapture } from "@/components/dwi/nodes/PhotoCapture";
import { ScanInput } from "@/components/dwi/nodes/ScanInput";
import { FileCapture } from "@/components/dwi/nodes/FileCapture";
import { Timer } from "@/components/dwi/nodes/Timer";
import { ComputedValue } from "@/components/dwi/nodes/ComputedValue";
import { QualityStatusField } from "@/components/dwi/nodes/QualityStatusField";
import { EquipmentRolesField } from "@/components/dwi/nodes/EquipmentRolesField";
import { PersonnelRolesField } from "@/components/dwi/nodes/PersonnelRolesField";
import { InspectionSignatures } from "@/components/dwi/nodes/InspectionSignatures";
import { ErrorTypesField } from "@/components/dwi/nodes/ErrorTypesField";
import { PartAnnotation } from "@/components/dwi/nodes/PartAnnotation";
import { PartCallout } from "@/components/dwi/nodes/PartCallout";
import { HarvestedComponentCapture } from "@/components/dwi/nodes/HarvestedComponentCapture";
import { DocumentLink } from "@/components/dwi/nodes/DocumentLink";
import { SlashCommand } from "@/lib/dwi/slash-command";

/** Shared TipTap extension list — used by both engineer (editable) and
 * operator (editable: false) editors. */
export const DWI_EXTENSIONS = [
    StarterKit,
    SlashCommand,
    MeasurementSpec,
    Callout,
    Media,
    DocumentLink,
    AttestationCheckpoint,
    MeasurementInput,
    TextInput,
    ChoiceInput,
    PhotoCapture,
    ScanInput,
    FileCapture,
    Timer,
    ComputedValue,
    QualityStatusField,
    EquipmentRolesField,
    PersonnelRolesField,
    InspectionSignatures,
    ErrorTypesField,
    PartAnnotation,
    PartCallout,
    HarvestedComponentCapture,
];
