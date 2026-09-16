/**
 * Search contracts for the routes that read query params.
 *
 * Each of these pages previously called `useSearch({ strict: false })` and cast
 * the result to a hand-written type. That cast asserts a shape over content the
 * user controls — the URL — so a malformed or hand-edited param reached page
 * code typed as something it isn't, and failed later at whatever consumed it.
 * These declare the shape once, on the route, so the router validates before the
 * component mounts and `useSearch` returns a genuinely typed object.
 *
 * Same strict/lenient split as `operator-runtime-search`: ids are `.uuid()` and
 * throw, because a wrong id means acting on the wrong record; free-text and
 * cosmetic filters use `.catch(undefined)` so a damaged link degrades to the
 * unfiltered view rather than an error page.
 *
 * No `.default()` anywhere — the router serialises defaults back into the URL,
 * which would start appending params to links that don't carry them today.
 */
import { z } from "zod";

/** `/dispositions/new` and `/dispositions/edit/$id` — prefill from a part or QR. */
export const DispositionSearch = z.object({
    partId: z.string().uuid().optional(),
    qualityReportId: z.string().uuid().optional(),
});
export type DispositionSearchParams = z.infer<typeof DispositionSearch>;

/** `/quality/capas/new` — comma-separated QualityReport ids to attach.
 *  Left as a plain string: the page splits and filters it, and one bad id in a
 *  list shouldn't block raising the CAPA. */
export const CreateCapaSearch = z.object({
    quality_reports: z.string().optional(),
});
export type CreateCapaSearchParams = z.infer<typeof CreateCapaSearch>;

/** Process flow viewer — `?id=` selects the process to render. */
export const ProcessFlowSearch = z.object({
    id: z.string().uuid().optional(),
});
export type ProcessFlowSearchParams = z.infer<typeof ProcessFlowSearch>;

/** `/quality/capas` — list filters arriving from a supplier or dashboard link.
 *
 *  `supplier` is `.uuid()` *and* `.catch(undefined)`: the endpoint declares a
 *  uuid, so a malformed one has to be dropped here or it is forwarded into a 400
 *  and the page renders "Couldn't load capas" over a filter the user never
 *  typed. Catching turns a stale link into the unfiltered list, which is what a
 *  list filter should degrade to.
 *
 *  `capa_type` is NOT validated here, and a bogus one still reaches the API and
 *  400s the list. It is a choice field server-side, but drf-spectacular emits
 *  `z.string()` for it -- as it does for `status` and `severity`, including the
 *  explicitly-declared ChoiceFilter -- so the contract carries no enum to
 *  validate against. Hardcoding the choices here would duplicate them and rot;
 *  the fix belongs in the schema, after which this should become
 *  `.catch(undefined)` on the generated enum like `supplier` above. */
export const CapaListSearch = z.object({
    supplier: z.string().uuid().optional().catch(undefined),
    capa_type: z.string().optional().catch(undefined),
});
export type CapaListSearchParams = z.infer<typeof CapaListSearch>;

/** `/signup` — invitation token. Opaque (not a UUID), and an invalid one has to
 *  reach the page so it can show "this invite is no longer valid". */
export const SignupSearch = z.object({
    token: z.string().optional(),
});
export type SignupSearchParams = z.infer<typeof SignupSearch>;
