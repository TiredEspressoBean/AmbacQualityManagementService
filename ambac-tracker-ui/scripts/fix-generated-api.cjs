/**
 * Post-process openapi-zod-client output (src/lib/api/generated.ts).
 *
 * The generator's zod emitter degrades two spectacular constructs to
 * z.unknown(), which poisons both runtime validation (the union accepts
 * anything) and TS inference (the whole union collapses to `unknown`):
 *
 *   - NullEnum  — spectacular's explicit-null enum for nullable choice fields
 *   - BlankEnum — spectacular's ""-member enum for blank=True choice fields
 *     (oneOf: [TheEnum, BlankEnum]); z.union([Enum, z.unknown()]) is what made
 *     e.g. disposition_type infer as `unknown`
 *
 * Both have exact zod equivalents. Applied idempotently after every regen.
 */
const fs = require("fs");

const path = "src/lib/api/generated.ts";
let text = fs.readFileSync(path, "utf8");

const replacements = [
    ["const NullEnum = z.unknown();", "const NullEnum = z.null();"],
    ["const BlankEnum = z.unknown();", 'const BlankEnum = z.literal("");'],
];

for (const [from, to] of replacements) {
    const count = text.split(from).length - 1;
    if (count > 1) {
        throw new Error(`Expected at most one occurrence of "${from}", found ${count}`);
    }
    text = text.replace(from, to);
}

fs.writeFileSync(path, text);
console.log("fix-generated-api: NullEnum/BlankEnum patched");