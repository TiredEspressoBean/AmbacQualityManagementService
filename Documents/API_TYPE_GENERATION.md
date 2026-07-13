# API Type Generation — Conventions & Known Pitfalls

*(2026-07-13. Distilled from a day of fighting the pipeline while wiring the
QA landing; every rule below traces to a concrete failure that strict client
validation or the typechecker caught.)*

## The pipeline

`schema.yaml` (drf-spectacular) → `bun run generate-api` produces **two**
artifacts in `ambac-tracker-ui/src/lib/api/`:

| Artifact | Generator | Trust it for |
|---|---|---|
| `generated.ts` | `openapi-zod-client` | the **client** (endpoint aliases) and the **runtime zod schemas** (strict response validation) |
| `generated-types.ts` | `openapi-typescript` | **compile-time types** (`components["schemas"][…]`) |

`generated.ts` also contains a printed block of exported TS types. **Do not
use it** — it is emitted by a separate code path from the zod schemas and has
been wrong about `additionalProperties` (`counts: {}` instead of an index
signature) and nullability on `$ref`'d fields. `generated-types.ts` got every
disputed case right.

## The post-process (`scripts/fix-generated-api.cjs`)

`openapi-zod-client` (latest, 1.18.3) degrades two spectacular constructs to
`z.unknown()`, which makes validation vacuous AND collapses TS inference:

- `NullEnum` (nullable choice fields) → patched to `z.null()`
- `BlankEnum` (`blank=True` choice fields, e.g. `disposition_type`, FPI
  `result`) → patched to `z.literal("")`

The script runs inside `generate-api` and is idempotent. If a new
`z.unknown()` degradation appears after a regen, extend the script — don't
cast around it in hooks.

## Hook typing convention

- **Hooks export their types; consumers never import from the generated
  files directly.** The hook is the single boundary where generated-artifact
  weirdness gets reconciled.
- **Derive, don't hand-write:** `export type MyDisposition =
  Pick<components["schemas"]["QuarantineDisposition"], "id" | …>` — a regen
  updates nullability/fields automatically. Hand-copied shapes drift (a
  hand-written type once invented a `created_at` the serializer doesn't
  expose).
- **Exception:** fields the schema types as `{}` — every
  `@extend_schema_field(serializers.DictField())` SerializerMethodField
  (the `*_info` blobs). Those force a hand-written shape in the hook, with a
  comment saying why. This is a **backend smell**: burn it down by declaring
  small inline serializers instead of DictField.
- If a cast is unavoidable, it lives **inside the hook's queryFn** with a
  comment naming the artifact bug it papers over.

## Backend schema rules (learned the hard way)

- **A ViewSet `list` action's response schema is force-wrapped in an array**
  by spectacular, no matter what `@extend_schema(responses=…)` says. If an
  endpoint returns one object, don't make it a `list` action — and prefer
  not returning envelope objects at all: return the flat row list (the
  `IncomingInspection` convention) and let clients derive counts.
- **`blank=True` choice fields must declare `allow_blank` on the serializer
  field**, or the schema enum omits `""` and strict validation rejects every
  row where the field is undecided (pending FPIs' `result`).
- **Name your enums.** A bare `type`/`status` field with a new choice set
  collides with existing ones and spectacular renames the *old* enum
  (`TypeEnum` → `TypeA18Enum`), breaking FE imports. Pin names in
  `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]` (both the new enum and the
  historical name), referencing a named choices constant.
- After any serializer/viewset change: regen schema + types and commit them
  in the same PR (CLAUDE.md rule) — and treat new spectacular *warnings* as
  errors; the one warning we ignored was the enum collision.
