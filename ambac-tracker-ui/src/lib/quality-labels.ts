// The words for an NCR's and a disposition's enums, in one place: each page that names a
// severity, a decision or a CAPA call reads them from here, so the same state never
// reads two ways.

export type Severity = "CRITICAL" | "MAJOR" | "MINOR";
export type DispositionType =
    "REWORK" | "REPAIR" | "SCRAP" | "USE_AS_IS" | "RETURN_TO_SUPPLIER" | "NOT_NONCONFORMANCE";

/** Severity as a picker offers it — what each level means. */
export const SEVERITY_LABEL: Record<Severity, string> = {
    CRITICAL: "Critical - Safety/Regulatory Impact",
    MAJOR: "Major - Functional Impact",
    MINOR: "Minor - Cosmetic Only",
};
export const SEVERITIES = (Object.keys(SEVERITY_LABEL) as Severity[])
    .map((value) => ({ value, label: SEVERITY_LABEL[value] }));

export const DECISION_LABEL: Record<DispositionType, string> = {
    REWORK: "Rework",
    REPAIR: "Repair (AS9100)",
    SCRAP: "Scrap",
    USE_AS_IS: "Use As Is",
    RETURN_TO_SUPPLIER: "Return to Supplier",
    // Only for a withdrawn finding (its capture voided and re-inspected PASS); closes the
    // decision.
    NOT_NONCONFORMANCE: "Not a nonconformance (result voided)",
};
export const DECISIONS = (Object.keys(DECISION_LABEL) as DispositionType[])
    .map((value) => ({ value, label: DECISION_LABEL[value] }));
export const decisionLabel = (t: string | null | undefined) =>
    t ? (DECISION_LABEL[t as DispositionType] ?? t) : null;

/** Decisions that accept nonconforming product: each needs a concession reference. */
export const CONCESSION_DECISIONS: readonly string[] = ["USE_AS_IS", "REPAIR"];

export const CAPA_DECISION_LABEL: Record<string, string> = {
    PROMOTED: "CAPA raised",
    NOT_REQUIRED: "No CAPA needed",
    DEFERRED: "Deferred",
};
