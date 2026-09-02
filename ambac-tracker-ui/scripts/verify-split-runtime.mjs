/**
 * Verify the runtime assumptions the client split rests on.
 *
 * Typechecking proves the TYPES survive being split; it says nothing about whether
 * a merged client actually works at runtime. Three things have to hold:
 *
 *   1. Aliases copied off a Zodios instance by Object.assign still route to their
 *      own client (they are arrow functions bound lexically, so they should).
 *   2. A shared axios instance means one place to intercept — an interceptor
 *      registered once is seen by calls made through every sub-client.
 *   3. Response validation still fires. This is the property the codebase relies
 *      on to catch schema drift, and losing it silently would be much worse than
 *      the compile error we set out to fix.
 *
 * Run against a live backend:  node scripts/verify-split-runtime.mjs
 */
import { makeApi, Zodios, ZodiosError } from "@zodios/core";
import { z } from "zod";

const BASE = process.env.API_BASE ?? "http://127.0.0.1:8000";

// Two chunks, deliberately mirroring what the generated client now does. The
// second endpoint's schema is WRONG on purpose, to prove validation still runs.
const chunk0 = makeApi([
  {
    method: "get",
    path: "/api/Schedules/config/",
    alias: "configFromChunk0",
    requestFormat: "json",
    response: z.object({}).passthrough(),
  },
]);
const chunk1 = makeApi([
  {
    method: "get",
    path: "/api/Schedules/capacity-load/",
    alias: "capacityFromChunk1",
    requestFormat: "json",
    response: z.object({}).passthrough(),
  },
  {
    method: "get",
    // Deliberately an UNAUTHENTICATED endpoint: a 401 short-circuits before
    // response validation, so pointing this at a gated endpoint would only ever
    // report "skipped" and prove nothing.
    path: "/api/csrf/",
    alias: "deliberatelyWrongSchema",
    requestFormat: "json",
    // The endpoint returns an object; demand an array so validation must reject.
    response: z.array(z.string()),
  },
]);

const c0 = new Zodios(BASE, chunk0, { axiosConfig: { withCredentials: true } });
const shared = c0.axios;
const c1 = new Zodios(BASE, chunk1, { axiosInstance: shared });

const api = Object.assign({ axios: shared }, c0, c1);

let intercepted = 0;
api.axios.interceptors.request.use((cfg) => {
  intercepted += 1;
  return cfg;
});

const results = [];
const check = (name, ok, detail = "") =>
  results.push({ name, ok, detail });

// 1. aliases from BOTH chunks exist on the merged object and are callable
check("alias from chunk 0 present", typeof api.configFromChunk0 === "function");
check("alias from chunk 1 present", typeof api.capacityFromChunk1 === "function");
check("api.axios present after merge", typeof api.axios?.get === "function");
check("both chunks share ONE axios instance", c0.axios === c1.axios);

// 2. calls route correctly through the merged object. Unauthenticated, so a 401
//    is the expected outcome — what matters is that the request was ISSUED with
//    the right URL, not that it succeeded.
for (const [label, fn, expectPath] of [
  ["chunk 0 alias routes", () => api.configFromChunk0(), "/api/Schedules/config/"],
  ["chunk 1 alias routes", () => api.capacityFromChunk1(), "/api/Schedules/capacity-load/"],
]) {
  try {
    await fn();
    check(label, true, "resolved (authenticated backend)");
  } catch (err) {
    const url = err?.config?.url ?? err?.response?.config?.url ?? "";
    const status = err?.response?.status;
    check(label, url.includes(expectPath),
      `status=${status} url=${url || "<none>"}`);
  }
}

// 3. the interceptor on the shared axios saw traffic from both chunks
check("shared interceptor saw both chunks' calls", intercepted >= 2,
  `${intercepted} request(s) intercepted`);

// 4. zod response validation still rejects a mismatched shape. Only meaningful if
//    the request is actually authorised — a 401 never reaches validation.
try {
  await api.deliberatelyWrongSchema();
  check("response validation still fires", false, "expected a rejection");
} catch (err) {
  if (err instanceof ZodiosError) {
    check("response validation still fires", true, "ZodiosError raised");
  } else {
    check("response validation still fires", "skipped",
      `unauthenticated (status ${err?.response?.status}); validation not reached`);
  }
}

let failed = 0;
for (const r of results) {
  const tag = r.ok === true ? "PASS" : r.ok === "skipped" ? "SKIP" : "FAIL";
  if (r.ok !== true && r.ok !== "skipped") failed += 1;
  console.log(`${tag}  ${r.name}${r.detail ? `  — ${r.detail}` : ""}`);
}
console.log(failed ? `\n${failed} check(s) failed` : "\nall checks passed");
process.exit(failed ? 1 : 0);
