/**
 * Reading an advancement result — `complete_step` / `advance_lot`.
 *
 * These answer HTTP 200 whether or not anything moved: `status` is the outcome.
 * "Blocked" is not always a refusal — under cohort advancement it can mean "your
 * unit is done; the lot moves when the rest are" — so it can't be a 4xx, and every
 * caller has to read `status`. Treating the 200 as success is how an operator once
 * saw "done" for a part that had not moved.
 */

export type AdvanceResultLike = {
    status: string;
    reason?: string | null;
    parts_advanced?: string[];
    blockers_by_part?: Record<string, string[]>;
    split_parts_advanced?: string[];
    split_parts_blocked?: Record<string, string[]>;
};

export type AdvanceOutcome = {
    /** Something advanced. */
    moved: boolean;
    /** How many units moved, cohort and split together. */
    advancedCount: number;
    /** This unit's own blockers — not another cohort member's. Empty without a unit. */
    mine: string[];
    /** Other units in the lot still blocked, i.e. what this one waits on. */
    othersWaiting: number;
    /** The lot stopped (cycle limit, routing error); `reason` says why. */
    halted: boolean;
    reason: string;
};

export function advanceOutcome(result: AdvanceResultLike, partId?: string): AdvanceOutcome {
    const advanced = [...(result.parts_advanced ?? []), ...(result.split_parts_advanced ?? [])];
    const byPart: Record<string, string[]> = {
        ...(result.blockers_by_part ?? {}),
        ...(result.split_parts_blocked ?? {}),
    };
    const mine = partId ? [...new Set(byPart[partId] ?? [])] : [];
    return {
        moved: result.status === "advanced" && advanced.length > 0,
        advancedCount: advanced.length,
        mine,
        othersWaiting: Object.keys(byPart).filter((id) => id !== partId).length,
        halted: result.status === "halted",
        reason: result.reason ?? "",
    };
}
