#!/usr/bin/env node
/**
 * Response-contract sweep.
 *
 * Calls every parameterless GET endpoint against a running dev server through
 * the generated Zodios client, so each response is validated by the same schema
 * the app uses at runtime. Prints every field where the server and the contract
 * disagree.
 *
 * Why this exists: a wrong response declaration is invisible to everything else
 * in this repo. `spectacular --fail-on-warn`, `tsc`, `eslint` and the backend
 * test suite were all green on a declaration that said
 * `content_object_info.id` was an integer when it is a CharField holding a
 * UUID -- which meant the zod client rejected every ApprovalRequests list
 * response, in the browser, and nowhere else. Only comparing a real response
 * against the schema finds that class.
 *
 *   bun scripts/check-response-contracts.mjs --login admin@demo.ambac.com:demo123
 *
 * Needs a TS-aware runtime (bun, or `bunx tsx`) because it imports the
 * generated client directly.
 *
 * Options:
 *   --base <url>       default http://localhost:5173 (the Vite proxy)
 *   --login <em:pw>    log in first and reuse the session cookies
 *   --cookie <str>     use a Cookie header directly instead of logging in
 *   --filter <substr>  only endpoints whose path contains this
 *   --limit <n>        stop after n endpoints
 *   --concurrency <n>  default 6
 *   --json <path>      also write the findings as JSON
 *
 * Exit code is 1 if any response fails validation, so this can gate a release
 * once the known failures are cleared.
 */

import { readFileSync, writeFileSync } from "node:fs";

// ---------------------------------------------------------------- arguments
function arg(name, fallback = undefined) {
    const i = process.argv.indexOf(`--${name}`);
    return i === -1 ? fallback : process.argv[i + 1];
}
const BASE = arg("base", "http://localhost:5173").replace(/\/$/, "");
const FILTER = arg("filter", "");
const LIMIT = Number(arg("limit", "0")) || Infinity;
const CONCURRENCY = Number(arg("concurrency", "6")) || 6;
const JSON_OUT = arg("json", "");

// generated.ts registers an axios interceptor that reads document.cookie at
// import time and reads location for the base URL. Neither exists outside a
// browser, so stub them before the import below.
globalThis.document ??= { cookie: "" };
globalThis.location ??= new URL(BASE);
globalThis.window ??= globalThis;

const generated = await import("../src/lib/api/generated.ts");

// ------------------------------------------------------------------- login
async function login(creds) {
    const [email, ...rest] = creds.split(":");
    const password = rest.join(":");
    const jar = new Map();

    const pre = await fetch(`${BASE}/api/csrf/`, { redirect: "manual" });
    absorb(pre, jar);

    const res = await fetch(`${BASE}/auth/login/`, {
        method: "POST",
        redirect: "manual",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": jar.get("csrftoken") ?? "",
            Cookie: cookieHeader(jar),
        },
        body: JSON.stringify({ email, username: email, password }),
    });
    absorb(res, jar);
    if (!res.ok && res.status !== 302) {
        throw new Error(`login failed: HTTP ${res.status} ${await res.text().catch(() => "")}`);
    }
    return cookieHeader(jar);
}
function absorb(res, jar) {
    for (const c of res.headers.getSetCookie?.() ?? []) {
        const [pair] = c.split(";");
        const i = pair.indexOf("=");
        if (i > 0) jar.set(pair.slice(0, i).trim(), pair.slice(i + 1).trim());
    }
}
const cookieHeader = (jar) => [...jar].map(([k, v]) => `${k}=${v}`).join("; ");

// ------------------------------------------------------------------- issues
function describeIssues(issues, max = 6) {
    const seen = new Set();
    const out = [];
    for (const i of issues) {
        const path = (i.path ?? []).join(".") || "(root)";
        // Collapse array indices: results.0.x and results.7.x are one defect.
        const key = path.replace(/\.\d+(\.|$)/g, ".*$1") + "|" + i.message;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(`${path.replace(/\.\d+(\.|$)/g, "[]$1")}: ${i.message}`);
        if (out.length >= max) break;
    }
    const extra = issues.length - out.length;
    return out.join("\n       ") + (extra > 0 ? `\n       …and ${extra} more` : "");
}

/** Pull a ZodError out of whatever zodios threw, or null if it wasn't one. */
function zodIssues(err) {
    for (const cand of [err?.cause, err, err?.error]) {
        if (Array.isArray(cand?.issues)) return cand.issues;
    }
    return null;
}

// ---------------------------------------------------------------------- main
const cookie = arg("cookie", "") || (arg("login") ? await login(arg("login")) : "");
if (!cookie) {
    console.error("Need --login <email:password> or --cookie <header>.");
    process.exit(2);
}

const client = generated.createApiClient(BASE, {
    axiosConfig: { headers: { Cookie: cookie, Accept: "application/json" } },
});

// createApiClient does `Object.assign({}, c0, …, c5)`, so the merged object
// carries every alias method but its `.api` table is whichever chunk was
// assigned last. Discovery therefore reads method/path/alias out of the source
// (which sees all six chunks); validation still goes through client[alias](),
// so the response is checked by the real schema, inline ones included.
const source = readFileSync(
    new URL("../src/lib/api/generated.ts", import.meta.url), "utf8",
);
const seenAlias = new Set();
const todo = [];
for (const m of source.matchAll(
    /method:\s*"(\w+)",\s*\n\s*path:\s*"([^"]+)",\s*\n\s*alias:\s*"(\w+)"/g,
)) {
    const [, method, path, alias] = m;
    if (method !== "get" || path.includes(":")) continue;
    if (FILTER && !path.includes(FILTER)) continue;
    if (seenAlias.has(alias)) continue;
    seenAlias.add(alias);
    if (typeof client[alias] !== "function") continue;
    todo.push({ path, alias });
    if (todo.length >= LIMIT) break;
}

console.log(`Sweeping ${todo.length} parameterless GET endpoints against ${BASE}\n`);

const failures = [];
const skipped = [];
let ok = 0;
let cursor = 0;

async function worker() {
    while (cursor < todo.length) {
        const { path, alias } = todo[cursor++];
        try {
            await client[alias]();
            ok++;
        } catch (err) {
            const issues = zodIssues(err);
            if (issues) {
                failures.push({ path, alias, issues });
                console.log(`  ✗ ${path}\n       ${describeIssues(issues)}`);
            } else {
                // 403/404/400 here means "not reachable as this user or without
                // params", not a contract defect. The sweep only judges bodies
                // it actually received.
                const status = err?.response?.status ?? err?.status;
                skipped.push({ path, alias, why: status ? `HTTP ${status}` : String(err?.message ?? err).slice(0, 90) });
            }
        }
    }
}
await Promise.all(Array.from({ length: CONCURRENCY }, worker));

console.log(`\n${"─".repeat(60)}`);
console.log(`validated : ${ok}`);
console.log(`mismatched: ${failures.length}`);
console.log(`skipped   : ${skipped.length}  (not reachable without params/permissions)`);

if (JSON_OUT) {
    writeFileSync(JSON_OUT, JSON.stringify({ failures, skipped }, null, 2));
    console.log(`\nwrote ${JSON_OUT}`);
}
process.exit(failures.length ? 1 : 0);
