/**
 * Search contract for the operator runtime deep link
 * (`/operator/steps/$stepId/substeps`).
 *
 * Lives in its own module so both the router and the page can import it: the
 * router lazy-imports the page, so having the page import `router.tsx` back
 * would close a cycle.
 *
 * Strict vs lenient is deliberate. The id params throw on a malformed value,
 * because this is a deep-link target and capturing against the wrong
 * step_execution is a quality-record problem — an error page is the correct
 * outcome. The cosmetic params (`at`, `unit`) use `.catch()` instead, so a
 * damaged or hand-edited URL resumes at the start rather than bricking a
 * station mid-shift; the page already clamps both.
 *
 * No `.default()` on purpose — the router serialises defaults back into the
 * URL, so one would start appending `?at=0` to links that don't carry it
 * today. The page's existing `search.at ?? 0` covers the absent case.
 */
import { z } from "zod";

export const OperatorRuntimeSearch = z.object({
    part: z.string().uuid().optional(),
    workOrder: z.string().uuid().optional(),
    /** Receiving inspection: the MaterialLot subject of this execution (no part/WO).
     *  Without it the runtime can't route back to the receiving page on complete. */
    material_lot: z.string().uuid().optional(),
    /** OSP return inspection: the OutsideProcessShipment subject of this execution. */
    osp_shipment: z.string().uuid().optional(),
    execution: z.string().uuid().optional(),
    /** Current substep index — drives the player + refresh/kiosk resume. */
    at: z.coerce.number().int().min(0).optional().catch(undefined),
    /** Receiving unit-by-unit: which sampled unit (1..n) is being inspected. */
    unit: z.coerce.number().int().min(1).optional().catch(undefined),
    /** Comma-separated list of remaining part ids to work in serial after the
     *  current one. Populated by `StartWorkDialog` when an operator checks
     *  multiple parts; consumed by `handleCompleteStep` to auto-advance to the
     *  next part. Empty/absent = no queue. */
    queue: z.string().optional(),
    debug: z.string().optional(),
});

export type OperatorRuntimeSearchParams = z.infer<typeof OperatorRuntimeSearch>;
