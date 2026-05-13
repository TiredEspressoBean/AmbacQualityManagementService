/**
 * Forbid `as any` type assertions.
 *
 * `as any` silently disables type checking at the cast site. Most cases
 * can be expressed more honestly:
 *   - `as never` — when bridging two equivalent zod/openapi-typescript
 *     shapes whose declared types diverge (zodios passthrough vs strict).
 *   - `as unknown` — when the source type genuinely isn't known.
 *   - A specific type — when the runtime shape is known.
 *
 * If a 3rd-party library genuinely lies about its types (recharts
 * callback payloads, assistant-ui adapters), opt out with a reason:
 *   // eslint-disable-next-line local/no-as-any -- recharts event.payload
 *   const data = e as any;
 *
 * The opt-out comment is required so a reader can see why the escape
 * hatch was necessary. The rule is registered at `'warn'` level so
 * existing casts don't fail CI — they should be audited and either
 * fixed or annotated over time.
 */

export default {
    meta: {
        type: "suggestion",
        docs: {
            description: "Disallow `as any` type assertions; prefer `as never`, `as unknown`, a specific type, or an annotated `eslint-disable` opt-out.",
        },
        schema: [],
        messages: {
            asAny:
                "Avoid `as any`. Use `as never`/`as unknown`/a specific type, or add `// eslint-disable-next-line local/no-as-any -- <reason>` with a justification.",
        },
    },
    create(context) {
        return {
            TSAsExpression(node) {
                if (node.typeAnnotation?.type === "TSAnyKeyword") {
                    context.report({ node, messageId: "asAny" });
                }
            },
        };
    },
};
