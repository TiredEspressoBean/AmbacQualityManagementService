/**
 * Forbid `renderCell: (p: any) => ...` inside table column definitions.
 *
 * Tied to the `Schema<"X">` + `createColumnHelper<T>()` pattern in
 * `ModelEditorPage`. When the helper is used and the row type is
 * imported from `@/lib/api/types`, the parameter type flows in
 * automatically — annotating it as `any` defeats the entire point.
 *
 * Why narrow this to renderCell instead of banning `any` repo-wide:
 * the eslint config deliberately keeps `@typescript-eslint/no-explicit-any`
 * off ("TypeScript flexibility during rapid development"). This rule
 * is the one column-definition-shaped exception so the typed-row
 * methodology is enforced, not just opt-in.
 *
 * Matches both:
 *   { renderCell: (p: any) => ... }
 *   renderCell: function (p: any) { ... }
 *
 * Does NOT match the same pattern outside renderCell (action cells,
 * generic event handlers) — they're out of scope for this rule.
 */

function paramHasAnyAnnotation(param) {
    if (!param || param.type !== "Identifier") return false;
    const ann = param.typeAnnotation?.typeAnnotation;
    return ann?.type === "TSAnyKeyword";
}

function functionFirstParamIsAny(node) {
    if (!node) return false;
    if (
        node.type !== "ArrowFunctionExpression" &&
        node.type !== "FunctionExpression"
    ) {
        return false;
    }
    return paramHasAnyAnnotation(node.params?.[0]);
}

export default {
    meta: {
        type: "problem",
        docs: {
            description:
                'Disallow `(p: any) =>` callbacks in `renderCell` properties. Use `createColumnHelper<Schema<"X">>()` so the row type is inferred.',
        },
        schema: [],
        messages: {
            anyInRenderCell:
                "Don't annotate renderCell's parameter as `any`. Use createColumnHelper<Schema<\"…\">>() so the row type flows in automatically.",
        },
    },
    create(context) {
        return {
            Property(node) {
                if (node.computed) return;
                const key = node.key.name ?? node.key.value;
                if (key !== "renderCell") return;
                if (!functionFirstParamIsAny(node.value)) return;
                context.report({
                    node: node.value.params[0],
                    messageId: "anyInRenderCell",
                });
            },
        };
    },
};