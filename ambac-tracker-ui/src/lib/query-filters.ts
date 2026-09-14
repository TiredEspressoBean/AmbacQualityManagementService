/**
 * Query filters that name a key without writing `queryKey:` inline.
 *
 * `local/no-inline-query-key` exists to stop cache keys being respelled at
 * every call site, but it reports ANY property named `queryKey` in the filter
 * object — including `{ queryKey: xOptions().queryKey }`, the form its own
 * message recommends. The two forms that satisfy it are passing an options
 * object whole, or a `predicate`.
 *
 * For an exact key, prefer passing the owning factory:
 * `invalidateQueries(xOptions(id))`. Use these helpers where there is no
 * single factory to point at — a root that spans several factories, or a
 * prefix shared by keys declared in another module.
 *
 * `matchKey` is not an approximation of the old behaviour. `partialMatchKey`
 * is the function TanStack itself applies to a `queryKey` filter (see
 * `matchQuery` in query-core), so `matchKey(k)` and `{ queryKey: k }` select
 * the same queries by construction.
 */
// From @tanstack/react-query, not @tanstack/query-core: query-core is only a
// transitive dependency here, so importing it directly works under bun's
// hoisting and breaks under a strict node_modules layout. react-query does
// `export * from '@tanstack/query-core'`, so this is the same function through
// the package we actually declare.
import { partialMatchKey } from "@tanstack/react-query";

type HasKey = { queryKey: readonly unknown[] };

/** Equivalent to `{ queryKey: key }` — prefix match, deep-compared. */
export const matchKey = (key: readonly unknown[]) => ({
    predicate: (q: HasKey) => partialMatchKey(q.queryKey, key),
});

/** Equivalent to `{ queryKey: [root] }` — everything under one root. */
export const underRoot = (root: string) => matchKey([root]);
