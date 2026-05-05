/**
 * Strict TypeScript types for API response models.
 *
 * `generated-types.ts` is produced by `openapi-typescript` from
 * PartsTracker/schema.yaml — see `bun run generate-types`. It exposes
 * every schema under `components["schemas"]`. Rather than hand-curating
 * a list of re-exported aliases (which would drift), we expose a single
 * `Schema<"Name">` lookup helper. The key is constrained to the actual
 * schema names in the spec, so the IDE autocompletes and TS will catch
 * stale names if a model is renamed upstream.
 *
 * Pair with `createColumnHelper<T>()` (in ModelEditorPage) to get
 * type-checked column renderers without the API client's permissive
 * passthrough zod schemas leaking into the UI layer.
 */
import type { components } from "./generated-types";

/**
 * Look up any schema from the OpenAPI spec by name.
 *
 * @example
 *   import type { Schema } from "@/lib/api/types";
 *   const col = createColumnHelper<Schema<"Parts">>();
 *   //                            ^^^^^^^^^^^^^^^^ IDE autocompletes all schema names
 */
export type Schema<K extends keyof components["schemas"]> = components["schemas"][K];