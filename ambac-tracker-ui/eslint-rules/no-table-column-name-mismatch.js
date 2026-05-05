/**
 * Catch table-column definitions where the `header` text describes one thing
 * (a name/identifier) but `renderCell` returns a field with a misleading
 * suffix (`_description`, `_id`, `_notes`).
 *
 * Targets the convention used across this codebase:
 *
 *   columns={[
 *     { header: "Step", renderCell: (p) => p.step_description }, // ← warned
 *   ]}
 *
 * False-positive guards:
 *   - If the header text already contains the field's suffix (e.g. header
 *     "Description" rendering `*_description`), the rule stays quiet.
 *   - If the renderCell uses a fallback chain like `p.step_name || p.step_description`,
 *     the rule looks at the FIRST candidate — the dev clearly preferred the
 *     name field, so no warning.
 *
 * Limitations:
 *   - Only matches `{ header, renderCell }` object form, not raw
 *     `<TableHead>` / `<TableCell>` JSX pairs (positional pairing inside a
 *     TableRow is harder to verify reliably).
 */

const SUSPECT_SUFFIXES = ["description", "id", "notes", "label_id"];

/** Words to strip from header text before noun-matching. */
const HEADER_NOISE_WORDS = new Set([
  "current", "previous", "next", "active", "the", "a", "an", "of", "for",
]);

function headerTokens(text) {
  return text
    .toLowerCase()
    .split(/[\s_/-]+/)
    .filter((w) => w && !HEADER_NOISE_WORDS.has(w));
}

/**
 * Walk a renderCell function body and return the first member-access
 * property name (e.g. `step_description` from `p.step_description` or
 * `p.step_description ?? "—"`). For fallback chains (`a || b`, `a ?? b`),
 * returns the LEFT operand's field — the developer's primary intent.
 */
function firstAccessedField(node) {
  if (!node) return null;
  switch (node.type) {
    case "MemberExpression":
      if (node.computed) return null;
      return node.property?.name ?? null;
    case "LogicalExpression": // a || b, a ?? b
      return firstAccessedField(node.left);
    case "ChainExpression":
      return firstAccessedField(node.expression);
    case "ConditionalExpression":
      return firstAccessedField(node.test) ?? firstAccessedField(node.consequent);
    case "ArrowFunctionExpression":
    case "FunctionExpression":
      if (node.body.type === "BlockStatement") {
        for (const stmt of node.body.body) {
          if (stmt.type === "ReturnStatement") {
            return firstAccessedField(stmt.argument);
          }
        }
        return null;
      }
      return firstAccessedField(node.body);
    case "JSXExpressionContainer":
      return firstAccessedField(node.expression);
    case "TSNonNullExpression":
    case "TSAsExpression":
      return firstAccessedField(node.expression);
    default:
      return null;
  }
}

export default {
  meta: {
    type: "problem",
    docs: {
      description:
        "Warn when a column object's `header` text doesn't match the suffix of the field rendered in `renderCell` — usually a `_description` / `_id` rendered under a name-style header.",
    },
    schema: [],
    messages: {
      mismatch:
        'Column header "{{ header }}" renders "{{ field }}" — that field ends in "_{{ suffix }}", which doesn\'t match the header. Did you mean "{{ suggestion }}"?',
    },
  },
  create(context) {
    return {
      ObjectExpression(node) {
        let headerProp = null;
        let renderCellProp = null;
        for (const prop of node.properties) {
          if (prop.type !== "Property" || prop.computed) continue;
          const key = prop.key.name ?? prop.key.value;
          if (key === "header") headerProp = prop;
          else if (key === "renderCell") renderCellProp = prop;
        }
        if (!headerProp || !renderCellProp) return;
        // header must be a string literal we can analyse
        const headerNode = headerProp.value;
        const headerText =
          headerNode.type === "Literal" && typeof headerNode.value === "string"
            ? headerNode.value
            : null;
        if (!headerText) return;

        const field = firstAccessedField(renderCellProp.value);
        if (!field) return;

        const suffix = SUSPECT_SUFFIXES.find((s) => field.endsWith(`_${s}`));
        if (!suffix) return;

        const tokens = headerTokens(headerText);
        // If the header itself mentions the suspect suffix, skip — header is honest.
        if (tokens.includes(suffix)) return;

        const prefix = field.slice(0, -("_" + suffix).length);
        // Only warn when the header noun matches the field prefix — that's the
        // "Step" → "step_description" mismatch we care about. Random fields
        // like `created_at_id` rendered under "Created" we don't bother with.
        if (!tokens.includes(prefix.replace(/_/g, ""))) return;

        context.report({
          node: renderCellProp.value,
          messageId: "mismatch",
          data: {
            header: headerText,
            field,
            suffix,
            suggestion: `${prefix}_name`,
          },
        });
      },
    };
  },
};