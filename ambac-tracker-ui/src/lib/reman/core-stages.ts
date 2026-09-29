/** A core's reman stages — the one place the UI names them.
 *
 * Labels mirror `Core.CORE_STATUS_CHOICES` (PartsTracker/Tracker/models/reman.py), the
 * source of truth. They used to live in four separate hand-copied maps, and the cores
 * list's copy stopped at the first four stages, so every stage added later — rebuild,
 * exchange-to-stock, harvest, authorisation — rendered as its raw enum. Add a stage
 * there and here, nowhere else.
 */

export const CORE_STAGE_LABEL: Record<string, string> = {
    RECEIVED: "Received",
    IN_DISASSEMBLY: "In Disassembly",
    DISASSEMBLED: "Disassembled",
    IN_REBUILD: "In Rebuild",
    REBUILT: "Rebuilt — ready to return",
    RETURNED: "Returned to customer",
    REBUILT_TO_STOCK: "Rebuilt to stock",
    AWAITING_AUTHORISATION: "Awaiting customer authorisation",
    DECLINED: "Scope declined — to be returned unrepaired",
    RETURNED_UNREPAIRED: "Returned unrepaired",
    HARVESTED: "Harvested to inventory",
    SCRAPPED: "Scrapped",
};

/** The stage's label; an unknown value is shown as-is rather than hidden. */
export function coreStageLabel(stage: string | null | undefined): string {
    if (!stage) return "—";
    return CORE_STAGE_LABEL[stage] ?? stage;
}

type Variant = "default" | "secondary" | "outline" | "destructive";

/** Badge tone. Loud for what needs someone (a decision outstanding, declined, scrapped),
 *  solid for work under way, quiet for endings. */
export function coreStageVariant(stage: string | null | undefined): Variant {
    switch (stage) {
        case "SCRAPPED":
        case "DECLINED":
            return "destructive";
        case "DISASSEMBLED":
        case "AWAITING_AUTHORISATION":
            return "outline";
        case "IN_DISASSEMBLY":
        case "IN_REBUILD":
        case "REBUILT":
            return "default";
        default:
            return "secondary";
    }
}
