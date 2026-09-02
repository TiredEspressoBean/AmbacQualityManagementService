/**
 * Split the generated zodios client into several smaller `makeApi` chunks.
 *
 * WHY: Zodios infers the whole API surface from its endpoint tuple, and every
 * endpoint adds type instantiations. Past roughly a thousand endpoints the
 * cumulative count crosses TypeScript's budget and the checker gives up:
 *
 *     generated.ts: error TS2589: Type instantiation is excessively deep
 *
 * When that happens tsc stops inferring the client, so EVERY `api.*` response
 * collapses to `{}` and ~95 errors appear in files that have nothing to do with
 * the change that tipped it over. It is miserable to debug, because every
 * reported error is downstream of one line.
 *
 * There is no compiler flag for this — the limit isn't configurable, so the only
 * lever is costing less. Each `makeApi([...])` call is inferred independently, so
 * N small tuples cost dramatically less than one large one (measured: 1 chunk of
 * 1998 endpoints fails; 4 chunks of 1998 and 8 chunks of 2997 are clean).
 *
 * HOW: chunk by a fixed SIZE, not a fixed count. Adding endpoints then adds
 * chunks rather than growing them, so the ceiling cannot return as the API grows.
 *
 * Every chunk shares ONE axios instance, so `api.axios` — used for CSRF setup,
 * the interceptors below it, and the direct import/export calls — behaves exactly
 * as it did with a single client. Zodios attaches endpoint aliases as own
 * properties holding arrow functions bound to their own client, so `Object.assign`
 * merges them and each still routes correctly. Response validation is a
 * per-client plugin and is unaffected: the zod check that catches schema drift
 * still fires.
 *
 * Prototype methods (`api.get`, `api.use`) are deliberately NOT carried over.
 * They read their client's own endpoint list, so on a merged object they would
 * silently see just one chunk. Nothing calls them; if anything ever does, a clear
 * "not a function" beats quietly wrong behaviour.
 *
 * Fails loudly rather than emitting a broken client: this is regex over generated
 * output, so if the generator's formatting changes it must stop the build, not
 * produce something that typechecks into nonsense.
 */
const fs = require("fs");

const PATH = "src/lib/api/generated.ts";
// Comfortably below where inference gets expensive, with room for endpoints whose
// schemas are unusually large.
const CHUNK_SIZE = 200;

const die = (msg) => {
    throw new Error(
        `split-api-client: ${msg}\n` +
        `The generated client's shape changed, so the endpoint split could not be ` +
        `applied. Fix this script rather than skipping it — without the split, ` +
        `passing ~1000 endpoints silently collapses every api.* response type to {}.`
    );
};

// Normalise to LF for the transform. Git checks this file out with CRLF on
// Windows while the generator writes LF, so every structural match below would
// otherwise depend on which produced the file on disk. Written back as LF, which
// is what the generator emits and what .gitattributes then converts.
let text = fs.readFileSync(PATH, "utf8").replace(/\r\n/g, "\n");

if (text.includes("const endpoints0 = makeApi([")) {
    console.log("split-api-client: already split, nothing to do");
    process.exit(0);
}

// --- 1. carve out the endpoints array -----------------------------------
const OPEN = "const endpoints = makeApi([";
const start = text.indexOf(OPEN);
if (start === -1) die(`could not find "${OPEN}"`);
const bodyStart = start + OPEN.length;
const end = text.indexOf("\n]);", bodyStart);
if (end === -1) die("could not find the end of the endpoints array");

const body = text.slice(bodyStart, end);
// Endpoints are emitted as "\n  {\n    method:" — split on that boundary.
const parts = body.split(/\n  \{\n    method:/).filter((p) => p.trim());
if (parts.length < 2) die(`parsed ${parts.length} endpoints; expected many`);
const endpoints = parts.map((p) => "  {\n    method:" + p.replace(/,\s*$/, ""));

const groups = [];
for (let i = 0; i < endpoints.length; i += CHUNK_SIZE) {
    groups.push(endpoints.slice(i, i + CHUNK_SIZE));
}

const chunkDecls = groups
    .map((g, i) => `const endpoints${i} = makeApi([\n${g.join(",\n")}\n]);`)
    .join("\n\n");

text = text.slice(0, start) + chunkDecls + text.slice(end + "\n]);".length);

// --- 2. replace the single client with N sharing one axios --------------
const clientStart = text.indexOf("export const api = BASE_URL");
if (clientStart === -1) die('could not find "export const api = BASE_URL"');
const clientEnd = text.indexOf("\n\n", text.indexOf("    });", clientStart));
if (clientEnd === -1) die("could not find the end of the api client construction");

const n = groups.length;
const names = Array.from({ length: n }, (_, i) => `client${i}`);

const clientBlock = `// Endpoint aliases are split across ${n} Zodios clients (see
// scripts/split-api-client.cjs for why). They share one axios instance, so
// \`api.axios\`, the interceptors below and CSRF handling are unchanged.
function zodiosOptions(axiosInstance?: unknown): ZodiosOptions {
  return {
    ...(axiosInstance ? { axiosInstance } : {}),
    axiosConfig: {
      withCredentials: true,
      paramsSerializer: (params: unknown) =>
        qs.stringify(params as Record<string, unknown>, { arrayFormat: "repeat" }),
      headers: {
        "X-CSRFToken": getCsrfToken() || "",
      },
    },
  } as ZodiosOptions;
}

const client0 = BASE_URL
  ? new Zodios(BASE_URL, endpoints0, zodiosOptions())
  : new Zodios(endpoints0, zodiosOptions());

// Later clients reuse client0's axios, so there is exactly one instance to
// configure and intercept.
const sharedAxios = client0.axios;
${names
    .slice(1)
    .map(
        (nm, i) =>
            `const ${nm} = BASE_URL\n  ? new Zodios(BASE_URL, endpoints${i + 1}, zodiosOptions(sharedAxios))\n  : new Zodios(endpoints${i + 1}, zodiosOptions(sharedAxios));`
    )
    .join("\n")}

export const api = Object.assign(
  { axios: sharedAxios },
${names.map((nm) => `  ${nm},`).join("\n")}
) as unknown as ${names.map((nm) => `typeof ${nm}`).join(" &\n  ")};`;

text = text.slice(0, clientStart) + clientBlock + text.slice(clientEnd);

// --- 3. createApiClient must cover every chunk too ----------------------
const factory = text.indexOf("export function createApiClient(");
if (factory === -1) die('could not find "export function createApiClient("');
const factoryBlock = `export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  const merge = (o?: ZodiosOptions): ZodiosOptions =>
    ({
      ...options,
      ...o,
      axiosConfig: {
        withCredentials: true,
        ...options?.axiosConfig,
        paramsSerializer: (params: unknown) =>
          qs.stringify(params as Record<string, unknown>, { arrayFormat: "repeat" }),
        headers: {
          "X-CSRFToken": getCsrfToken() || "",
          ...options?.axiosConfig?.headers,
        },
        ...o?.axiosConfig,
      },
    }) as ZodiosOptions;
  // Separate consts, NOT an array literal: collecting the clients into an array
  // makes TypeScript infer a tuple of every client type at once, which is itself
  // enough to blow the instantiation budget (TS2589) and undo the split.
  const c0 = new Zodios(baseUrl, endpoints0, merge());
${groups
    .slice(1)
    .map(
        (_, i) =>
            `  const c${i + 1} = new Zodios(baseUrl, endpoints${i + 1}, merge({ axiosInstance: c0.axios } as ZodiosOptions));`
    )
    .join("\n")}
  return Object.assign(
    { axios: c0.axios },
${groups.map((_, i) => `    c${i},`).join("\n")}
  ) as unknown as ${names.map((nm) => `typeof ${nm}`).join(" &\n    ")};
}`;
text = text.slice(0, factory) + factoryBlock + "\n";

fs.writeFileSync(PATH, text);
console.log(
    `split-api-client: ${endpoints.length} endpoints across ${n} clients ` +
    `(chunk size ${CHUNK_SIZE})`
);
