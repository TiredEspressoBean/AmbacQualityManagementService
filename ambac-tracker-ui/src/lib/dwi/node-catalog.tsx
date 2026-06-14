/**
 * DWI node catalog — single source of truth for insertable blocks.
 *
 * Every picker (the ribbon, the `/` slash menu, a future gutter `+`) is just a
 * *view* over this array. Adding a node = one entry here, not another glyph in
 * a toolbar. Lives in `lib/` (not the page) so both the editor page and the
 * shared slash-command extension can import it without a cycle.
 */
import type { ReactNode } from "react";
import {
    AlertTriangle,
    Bug,
    Calculator,
    Camera,
    CheckSquare,
    ClipboardCheck,
    FileText,
    Gauge,
    Image as ImageIcon,
    ListChecks,
    MapPin,
    PackageOpen,
    Paperclip,
    PenLine,
    Ruler,
    ScanLine,
    ScanSearch,
    ShieldCheck,
    Timer as TimerIcon,
    Type,
    Users,
    Wrench,
} from "lucide-react";
import type { Editor } from "@tiptap/react";

import {
    SAMPLE_ATTESTATION_CONFIRM,
    SAMPLE_ATTESTATION_SIGNATURE,
    SAMPLE_CALLOUT_CAUTION,
    SAMPLE_CHOICE_RADIO,
    SAMPLE_COMPUTED_TRUE_POSITION,
    SAMPLE_FILE,
    SAMPLE_MEASUREMENT_INPUT,
    SAMPLE_MEASUREMENT_SPEC,
    SAMPLE_MEDIA,
    SAMPLE_DOCUMENT_LINK,
    SAMPLE_PHOTO,
    SAMPLE_SCAN,
    SAMPLE_TEXT_INPUT_SHORT,
    SAMPLE_TIMER_COUNTDOWN,
    SAMPLE_QUALITY_STATUS,
    SAMPLE_EQUIPMENT_ROLES,
    SAMPLE_PERSONNEL_ROLES,
    SAMPLE_INSPECTION_SIGNATURES,
    SAMPLE_ERROR_TYPES,
    SAMPLE_PART_ANNOTATION,
    SAMPLE_PART_CALLOUT,
    SAMPLE_HARVESTED_COMPONENT_CAPTURE,
    QUALITY_REPORT_BUNDLE,
} from "@/lib/dwi/samples";
import { withFreshNodeId, type TemplateNode } from "@/lib/dwi/node-id";

export type CatalogEntry = {
    id: string;
    label: string;
    description: string;
    icon: ReactNode;
    /** Extra search terms for the slash menu (synonyms the label misses). */
    keywords?: string;
    /** TipTap sample node, or an array for multi-node templates/bundles. */
    content: object | object[];
};
export type CatalogCategory = { key: string; label: string; entries: CatalogEntry[] };

export const NODE_CATALOG: CatalogCategory[] = [
    {
        key: "text",
        label: "Text & Layout",
        entries: [
            { id: "callout", label: "Callout", description: "Caution / note box", keywords: "warning danger safety", icon: <AlertTriangle className="h-4 w-4" />, content: SAMPLE_CALLOUT_CAUTION },
            { id: "media", label: "Media", description: "Image / video", keywords: "picture photo video", icon: <ImageIcon className="h-4 w-4" />, content: SAMPLE_MEDIA },
            { id: "docLink", label: "Document link", description: "Reference a controlled doc", keywords: "reference attachment spec", icon: <FileText className="h-4 w-4" />, content: SAMPLE_DOCUMENT_LINK },
        ],
    },
    {
        key: "capture",
        label: "Capture",
        entries: [
            { id: "photo", label: "Photo", description: "Operator takes a photo", keywords: "camera image", icon: <Camera className="h-4 w-4" />, content: SAMPLE_PHOTO },
            { id: "scan", label: "Scan", description: "Barcode / QR scan", keywords: "barcode qr serial", icon: <ScanLine className="h-4 w-4" />, content: SAMPLE_SCAN },
            { id: "file", label: "File", description: "Attach a file", keywords: "upload attachment", icon: <Paperclip className="h-4 w-4" />, content: SAMPLE_FILE },
            { id: "textInput", label: "Text input", description: "Short / long text", keywords: "note comment field", icon: <Type className="h-4 w-4" />, content: SAMPLE_TEXT_INPUT_SHORT },
            { id: "choice", label: "Choice", description: "Radio / select", keywords: "select dropdown option", icon: <ListChecks className="h-4 w-4" />, content: SAMPLE_CHOICE_RADIO },
            { id: "timer", label: "Timer", description: "Countdown / stopwatch", keywords: "clock duration cure", icon: <TimerIcon className="h-4 w-4" />, content: SAMPLE_TIMER_COUNTDOWN },
            { id: "measureInput", label: "Measurement", description: "Numeric + spec bounds", keywords: "dimension caliper gauge value", icon: <Ruler className="h-4 w-4" />, content: SAMPLE_MEASUREMENT_INPUT },
            { id: "measureSpec", label: "Measurement spec", description: "Nominal / tolerance", keywords: "tolerance nominal limit", icon: <Gauge className="h-4 w-4" />, content: SAMPLE_MEASUREMENT_SPEC },
            { id: "computed", label: "Computed", description: "Formula value", keywords: "calculate formula derived", icon: <Calculator className="h-4 w-4" />, content: SAMPLE_COMPUTED_TRUE_POSITION },
        ],
    },
    {
        key: "quality",
        label: "Quality",
        entries: [
            { id: "qualityStatus", label: "Quality status", description: "PASS / FAIL / PENDING", keywords: "pass fail accept reject", icon: <ShieldCheck className="h-4 w-4" />, content: SAMPLE_QUALITY_STATUS },
            { id: "defects", label: "Defect findings", description: "Pick error types", keywords: "error nonconformance reject", icon: <Bug className="h-4 w-4" />, content: SAMPLE_ERROR_TYPES },
            { id: "inspectionSign", label: "Inspection signatures", description: "Detected / verified", keywords: "signoff approve verify", icon: <PenLine className="h-4 w-4" />, content: SAMPLE_INSPECTION_SIGNATURES },
            { id: "attestation", label: "Attestation", description: "Confirm checkpoint", keywords: "confirm acknowledge checkbox", icon: <CheckSquare className="h-4 w-4" />, content: SAMPLE_ATTESTATION_CONFIRM },
            { id: "signatureGate", label: "Sign-off", description: "Require a signature", keywords: "signature approve gate", icon: <PenLine className="h-4 w-4" />, content: SAMPLE_ATTESTATION_SIGNATURE },
        ],
    },
    {
        key: "roles",
        label: "Roles",
        entries: [
            { id: "equipmentRoles", label: "Equipment + roles", description: "Required equipment", keywords: "tool machine fixture", icon: <Wrench className="h-4 w-4" />, content: SAMPLE_EQUIPMENT_ROLES },
            { id: "personnelRoles", label: "Personnel + roles", description: "Required personnel", keywords: "people operator staff", icon: <Users className="h-4 w-4" />, content: SAMPLE_PERSONNEL_ROLES },
        ],
    },
    {
        key: "threed",
        label: "3D & Teardown",
        entries: [
            { id: "partCallout", label: "Callouts (3D)", description: "Numbered guidance balloons on the model", keywords: "3d callout balloon label point guide annotate", icon: <MapPin className="h-4 w-4" />, content: SAMPLE_PART_CALLOUT },
            { id: "partAnnotation", label: "Defect annotation (3D)", description: "Operator marks defects on the model", keywords: "3d defect inspection annotate heatmap quality", icon: <ScanSearch className="h-4 w-4" />, content: SAMPLE_PART_ANNOTATION },
            { id: "harvested", label: "Harvested components", description: "Teardown capture", keywords: "reman disassembly core", icon: <PackageOpen className="h-4 w-4" />, content: SAMPLE_HARVESTED_COMPONENT_CAPTURE },
        ],
    },
    {
        key: "templates",
        label: "Templates",
        entries: [
            { id: "qaBundle", label: "QA inspection bundle", description: "Photo + scan + sign-off set", keywords: "bundle inspection template set", icon: <ClipboardCheck className="h-4 w-4" />, content: QUALITY_REPORT_BUNDLE },
        ],
    },
];

export const ALL_ENTRIES: CatalogEntry[] = NODE_CATALOG.flatMap((c) => c.entries);

/** Seed for the ★Frequent tab before any personal recency exists. */
export const DEFAULT_FREQUENT = ["measureInput", "photo", "signatureGate", "scan", "qualityStatus", "callout", "qaBundle"];
export const RECENT_KEY = "dwi.recentNodes";

export function loadRecent(): string[] {
    try {
        const raw = localStorage.getItem(RECENT_KEY);
        return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
        return [];
    }
}

export function rememberRecent(id: string): string[] {
    const next = [id, ...loadRecent().filter((x) => x !== id)].slice(0, 8);
    try {
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    } catch {
        /* ignore */
    }
    return next;
}

/** Insert a catalog entry, minting fresh node_ids so each insert is unique. */
export function insertEntry(editor: Editor, entry: CatalogEntry) {
    const raw = entry.content;
    const content = Array.isArray(raw)
        ? raw.map((n) => withFreshNodeId(n as TemplateNode))
        : withFreshNodeId(raw as TemplateNode);
    editor.chain().focus().insertContent(content as never).run();
}

/** Case-insensitive filter across label + keywords + id (for the slash menu). */
export function filterEntries(query: string): CatalogEntry[] {
    const q = query.trim().toLowerCase();
    if (!q) return ALL_ENTRIES;
    return ALL_ENTRIES.filter((e) =>
        `${e.label} ${e.keywords ?? ""} ${e.id}`.toLowerCase().includes(q),
    );
}
