import { api } from "@/lib/api/generated";

/**
 * The generated client's function for `/api/<endpoint>/<action>`, if the backend has one.
 *
 * The client names functions after the route with `-` and `/` turned into `_`
 * (`Error-types` → `api_Error_types_…`, `notifications/external-contacts` →
 * `api_notifications_external_contacts_…`). Looking one up by the raw endpoint missed
 * every hyphenated route. What exists here is what the backend's schema has, so this is
 * also how a toolbar knows which models import and export at all.
 *
 * Dynamic alias lookup is one of the few places `any` is genuinely the right tool. A
 * Record<string, unknown> cast needs `as unknown as` (trading one lint rule for the
 * double-cast one), and `keyof typeof api` makes tsc give up ("Type instantiation is
 * excessively deep") against a 1000-endpoint client. Callers' `typeof … === "function"`
 * guard is what makes this safe.
 */
export const endpointFn = (apiEndpoint: string, action: string): unknown =>
    // eslint-disable-next-line local/no-as-any -- dynamic API alias lookup by string; see above
    (api as any)[`api_${apiEndpoint.replace(/[-/]/g, "_")}_${action}`];

/** True when the backend exposes `/api/<endpoint>/<action>`. */
export const hasEndpoint = (apiEndpoint: string, action: string): boolean =>
    typeof endpointFn(apiEndpoint, action) === "function";
