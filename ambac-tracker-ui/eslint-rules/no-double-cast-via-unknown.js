/**
 * Forbid `as unknown as T` double casts.
 *
 * The double-cast pattern `(value as unknown) as Target` is a deliberate
 * type-system bypass — TypeScript is telling you "these types aren't
 * compatible" and the double cast forces it anyway. Almost always either:
 *
 *   1. Hiding a real bug (accessing a field that doesn't exist on the
 *      declared type).
 *   2. A symptom of API spec drift (backend exposes a field that drf-
 *      spectacular didn't emit). Fix the serializer instead.
 *   3. A genuine FFI seam where a 3rd-party library's types don't match
 *      its runtime contract — in which case opt out with a reason:
 *
 *      // eslint-disable-next-line local/no-double-cast-via-unknown -- assistant-ui attachment.source not in declared types
 *      const src = (attachment as unknown as { source: string }).source;
 *
 * Single `as unknown` (followed by a type guard, not another cast) is
 * fine and is NOT flagged by this rule — that's the legitimate way to
 * receive opaque data from `JSON.parse`, `postMessage`, etc.
 */

export default {
    meta: {
        type: "suggestion",
        docs: {
            description:
                "Disallow the `as unknown as T` double-cast pattern. Prefer fixing the type, narrowing with a type guard, or annotating the opt-out.",
        },
        schema: [],
        messages: {
            doubleCast:
                "Avoid `as unknown as T` double casts — they bypass TypeScript's safety. Prefer fixing the underlying type, narrowing with a type guard, or annotating the opt-out with `// eslint-disable-next-line local/no-double-cast-via-unknown -- <reason>`.",
        },
    },
    create(context) {
        return {
            TSAsExpression(node) {
                // We're looking for `(inner as unknown) as Target`.
                // Outer `as T` where T != unknown.
                if (node.typeAnnotation?.type === "TSUnknownKeyword") return;

                const inner = node.expression;
                if (
                    inner?.type === "TSAsExpression" &&
                    inner.typeAnnotation?.type === "TSUnknownKeyword"
                ) {
                    context.report({ node, messageId: "doubleCast" });
                }
            },
        };
    },
};
