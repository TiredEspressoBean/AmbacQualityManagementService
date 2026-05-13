/**
 * Forbid inline `queryKey:` in TanStack Query calls.
 *
 * Cache-shape collisions happen when two writers share a queryKey but
 * disagree on the value's shape, OR when an invalidator references a key
 * that has since been renamed at the factory. The fix in both directions
 * is one source of truth: a `queryOptions()` factory that owns the
 * (queryKey, queryFn, return type) triple. All callers consume the
 * factory's output — for reads via spread, for invalidation via
 * `xOptions()` or `xOptions().queryKey`.
 *
 * This rule forbids `queryKey:` as a property of the option object
 * passed directly to:
 *
 * **Data-reading APIs (writes shape into cache):**
 *   - useQuery / useSuspenseQuery / useInfiniteQuery / useSuspenseInfiniteQuery
 *   - prefetchQuery / prefetchInfiniteQuery
 *   - fetchQuery / fetchInfiniteQuery
 *   - ensureQueryData
 *
 * **Cache-management APIs (drifts when factory key renames):**
 *   - invalidateQueries / refetchQueries / cancelQueries / removeQueries
 *   - resetQueries
 *
 * Inside `queryOptions({ queryKey: ..., queryFn: ... })` the property
 * is allowed — that IS the canonical declaration site.
 *
 * `setQueryData(queryKey, ...)` and `getQueryData(queryKey)` take a
 * positional queryKey arg (not an object option). They are not linted by
 * this rule — flagging those requires a separate positional-arg check.
 * Migrate them to `setQueryData(xOptions().queryKey, ...)` manually.
 *
 * Opt out with a justification:
 *   // eslint-disable-next-line local/no-inline-query-key -- <reason>
 */

const FORBIDDEN_CALLEES = new Set([
    // Data-reading APIs
    "useQuery",
    "useSuspenseQuery",
    "useInfiniteQuery",
    "useSuspenseInfiniteQuery",
    "prefetchQuery",
    "fetchQuery",
    "ensureQueryData",
    "prefetchInfiniteQuery",
    "fetchInfiniteQuery",
    // Cache-management APIs
    "invalidateQueries",
    "refetchQueries",
    "cancelQueries",
    "removeQueries",
    "resetQueries",
]);

function getCalleeName(callee) {
    if (callee.type === "Identifier") return callee.name;
    if (callee.type === "MemberExpression" && callee.property.type === "Identifier") {
        return callee.property.name;
    }
    return null;
}

export default {
    meta: {
        type: "problem",
        docs: {
            description:
                "Disallow inline queryKey in TanStack Query calls. Define a queryOptions() factory and pass its output (or its .queryKey) instead.",
        },
        schema: [],
        messages: {
            inlineKey:
                "Avoid inline `queryKey:` in `{{callee}}`. Define a `xOptions = () => queryOptions({ queryKey, queryFn })` factory and pass `xOptions()` (or `xOptions().queryKey` for cache-management calls) here. This prevents cache-shape drift between writers and stale keys between invalidators and factories.",
        },
    },
    create(context) {
        return {
            CallExpression(node) {
                const name = getCalleeName(node.callee);
                if (!name || !FORBIDDEN_CALLEES.has(name)) return;

                const firstArg = node.arguments[0];
                if (!firstArg || firstArg.type !== "ObjectExpression") return;

                for (const prop of firstArg.properties) {
                    if (
                        prop.type === "Property" &&
                        !prop.computed &&
                        ((prop.key.type === "Identifier" && prop.key.name === "queryKey") ||
                            (prop.key.type === "Literal" && prop.key.value === "queryKey"))
                    ) {
                        context.report({
                            node: prop,
                            messageId: "inlineKey",
                            data: { callee: name },
                        });
                    }
                }
            },
        };
    },
};
