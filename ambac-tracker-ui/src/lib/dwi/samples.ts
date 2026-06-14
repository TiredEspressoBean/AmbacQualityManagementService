/** Sample / seed node JSON snippets — re-exported from each node module so
 * toolbars and seed documents can import them from one place. */
export { SAMPLE_MEASUREMENT_SPEC } from "@/components/dwi/nodes/MeasurementSpec";
export {
    SAMPLE_CALLOUT_CAUTION,
    SAMPLE_CALLOUT_NOTE,
} from "@/components/dwi/nodes/Callout";
export { SAMPLE_MEDIA } from "@/components/dwi/nodes/Media";
export { SAMPLE_DOCUMENT_LINK } from "@/components/dwi/nodes/DocumentLink";
export {
    SAMPLE_ATTESTATION_CONFIRM,
    SAMPLE_ATTESTATION_SIGNATURE,
} from "@/components/dwi/nodes/AttestationCheckpoint";
export { SAMPLE_MEASUREMENT_INPUT } from "@/components/dwi/nodes/MeasurementInput";
export {
    SAMPLE_TEXT_INPUT_SHORT,
    SAMPLE_TEXT_INPUT_LONG,
} from "@/components/dwi/nodes/TextInput";
export {
    SAMPLE_CHOICE_RADIO,
    SAMPLE_CHOICE_SELECT,
} from "@/components/dwi/nodes/ChoiceInput";
export { SAMPLE_PHOTO } from "@/components/dwi/nodes/PhotoCapture";
export { SAMPLE_SCAN } from "@/components/dwi/nodes/ScanInput";
export { SAMPLE_FILE } from "@/components/dwi/nodes/FileCapture";
export {
    SAMPLE_TIMER_COUNTDOWN,
    SAMPLE_TIMER_STOPWATCH,
} from "@/components/dwi/nodes/Timer";
export { SAMPLE_COMPUTED_TRUE_POSITION } from "@/components/dwi/nodes/ComputedValue";
export { SAMPLE_QUALITY_STATUS } from "@/components/dwi/nodes/QualityStatusField";
export { SAMPLE_EQUIPMENT_ROLES } from "@/components/dwi/nodes/EquipmentRolesField";
export { SAMPLE_PERSONNEL_ROLES } from "@/components/dwi/nodes/PersonnelRolesField";
export { SAMPLE_INSPECTION_SIGNATURES } from "@/components/dwi/nodes/InspectionSignatures";
export { SAMPLE_ERROR_TYPES } from "@/components/dwi/nodes/ErrorTypesField";
export { SAMPLE_PART_ANNOTATION } from "@/components/dwi/nodes/PartAnnotation";
export { SAMPLE_PART_CALLOUT } from "@/components/dwi/nodes/PartCallout";
export { SAMPLE_HARVESTED_COMPONENT_CAPTURE } from "@/components/dwi/nodes/HarvestedComponentCapture";

// ---------------------------------------------------------------------------
// Bundles — pre-composed sets of nodes for "I want a whole inspection
// substep, not five individual inserts." Each entry is a sample node JSON.
// Authoring code is expected to run `withFreshNodeId()` on every entry
// before inserting so node_ids stay unique.
// ---------------------------------------------------------------------------

import { SAMPLE_QUALITY_STATUS as _SAMPLE_QUALITY_STATUS } from "@/components/dwi/nodes/QualityStatusField";
import { SAMPLE_EQUIPMENT_ROLES as _SAMPLE_EQUIPMENT_ROLES } from "@/components/dwi/nodes/EquipmentRolesField";
import { SAMPLE_INSPECTION_SIGNATURES as _SAMPLE_INSPECTION_SIGNATURES } from "@/components/dwi/nodes/InspectionSignatures";
import { SAMPLE_ERROR_TYPES as _SAMPLE_ERROR_TYPES } from "@/components/dwi/nodes/ErrorTypesField";

/** Minimum capture set to satisfy a `QualityReports` row when the
 *  containing substep has `is_inspection_point=True`. Covers status,
 *  detected-by signature, production machine, and (optional) defect
 *  findings. Engineers who want more (measurements, multiple signatures,
 *  photo attachment) compose those nodes around the bundle. */
export const QUALITY_REPORT_BUNDLE = [
    _SAMPLE_QUALITY_STATUS,
    _SAMPLE_EQUIPMENT_ROLES,
    _SAMPLE_INSPECTION_SIGNATURES,
    _SAMPLE_ERROR_TYPES,
];
