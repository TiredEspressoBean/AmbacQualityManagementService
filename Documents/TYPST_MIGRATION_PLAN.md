# Typst Migration Plan — Full Replacement for Playwright PDF Pipeline

**Last Updated:** April 2026
**Status:** Planning (pre-launch — no production users)
**Owner:** TBD

---

## Executive Summary

Replace the Playwright-based PDF generation pipeline with Typst before
the first external user ships. Since no customers exist yet, this is
cheap: no data migration, no regulatory re-validation, no parallel
running, no rollback pressure. The choice being made now is which
engine the product launches on.

Typst is the right answer because:

1. **Security by design.** Playwright's architecture requires solving
   cross-tenant param validation plus authenticated session forwarding
   or signed URLs. Typst takes an ORM context dict directly — no HTTP
   round-trip, no auth surface, no way to smuggle cross-tenant IDs
   through the rendering pipeline.

2. **Cost.** Playwright requires a warm Chromium instance (~500 MB idle
   RAM per service) and adds ~400 MB to the Docker image. Typst is a
   ~15 MB pip install with zero idle RAM overhead.

3. **Deployment simplicity.** Playwright needs `libgbm`, `libnss3`,
   `libatk-bridge2.0`, fonts, and `playwright install --with-deps
   chromium`. Typst needs only the pip package and bundled fonts.

4. **Better typography for compliance documents.** Proper typesetting
   vs. browser-rendered HTML. Deterministic output. One mental model
   (one engine, one pattern, one set of templates).

---

## Current State (as of April 2026)

### Backend

- `Tracker/reports/` subpackage contains viewset, Celery task, and
  `PdfGenerator` service (already extracted from the monolith as of
  integration-framework branch work).
- `PdfGenerator` uses a warm Chromium instance via `playwright` Python
  package. Browser pool restarts every 500 requests.
- Three report types implemented: `spc`, `capa`, `quality_report`. Each
  loads a React print page in Playwright and converts to PDF.
- `REPORT_CONFIG` dict maps report type names to Playwright rendering
  config (route template, wait selector, page dimensions).
- `ReportViewSet` exposes `/api/reports/generate/` (async via Celery) and
  `/api/reports/download/` (sync). Both accept `{report_type, params}`.
- `GeneratedReport` audit model tracks every report generation.
- `params` currently accepts a raw `DictField` with no tenant validation.

### Frontend

- React print pages for `SpcPrintPage`, `CapaPrintPage`,
  `QualityReportPrintPage`. Each fetches data via existing hooks,
  renders for print, sets `data-print-ready` when loaded.
- `GenerateDocumentDialog` component handles download/email/DMS-save.
- `useReportEmail.ts` hook calls backend.
- SPC print page currently uses **mock data**, not the real SPC hooks.

### Infrastructure

- Dockerfile installs Playwright Python package but does NOT install
  Chromium or system deps (known gap).
- Railway deployment has not been load-tested with real PDF generation.
- Memory allocation for Backend and celery-worker services is at default.

### Outstanding security gap

Per security review, `params` is accepted raw without validation that
referenced IDs (CAPA id, process id, measurement id, etc.) belong to
the user's tenant. Playwright runs unauthenticated against the frontend,
meaning Typst migration automatically eliminates this vector.

---

## Target State

### Backend

- `Tracker/reports/adapters/` — one adapter class per report type,
  inheriting from `ReportAdapter` base.
- `Tracker/reports/services/typst_generator.py` — thin wrapper around
  `typst.compile()` with font path configuration.
- `Tracker/reports/services/registry.py` — list of adapter dotted paths,
  lazy-loaded (mirrors `integrations/services/registry.py` pattern).
- `Tracker/reports/templates/` — directory of `.typ` files, one per
  report type, plus `_common/` shared includes.
- Per-adapter `param_serializer_class` validates all params against
  the user's tenant before rendering begins.
- `PdfGenerator.generate()` dispatches through the adapter; no
  Playwright fallback.

### Frontend

- React print pages deleted (SpcPrintPage, CapaPrintPage,
  QualityReportPrintPage).
- `GenerateDocumentDialog` unchanged — works identically from the
  caller's perspective.
- No visible change to end users.

### Infrastructure

- No Chromium in Docker image.
- Noto Sans + Noto Serif installed via `fonts-noto-core` apt package
  in the Docker image.
- Railway memory allocation can be reduced on Backend and
  celery-worker services (no warm browser to hold).

---

## What Gets Added

### Python packages

| Package | Version | Purpose |
|---------|---------|---------|
| `typst` | `0.14.8` (as of Feb 2026) | Python binding for Typst compiler |
| `pydantic` | `>=2.13` | Typed context models at adapter → template boundary |

`typst` provides pre-built manylinux wheels for CPython 3.8+ — no Rust
toolchain needed at install time, `pip install typst` just works on
Railway's Debian-based Python 3.12 image. Maintained by `messense`;
API confirmed against [typst-py GitHub](https://github.com/messense/typst-py).

`pydantic` is already installed transitively via `pydantic-settings` but
should be declared explicitly in `requirements.txt`. Every adapter's
`build_context()` returns a Pydantic model instance, converted to dict
via `.model_dump(mode='json')` before being passed to Typst. Pydantic's
runtime validation catches the most common drift: wrong types, missing
fields, unexpected nulls from ORM queries.

### Directory structure

Sprint scope: two reports (CofC + SPC) + the shared framework. Other
adapter filenames listed below are future placeholders — not built in
the sprint.

```
PartsTracker/
  typst_packages/                    # Vendored Typst Universe packages
    preview/
      cetz/0.3.2/                   # Drawing + charts for SPC
      diagraph/0.3.0/               # Graphviz-based DAG rendering
  Tracker/reports/
    adapters/
      __init__.py
      base.py                        # ReportAdapter abstract base + Pydantic contract
      cert_of_conformance.py         # [sprint]
      spc.py                         # [sprint]
      # future: part_traveler, ncr_report, fai_form_3, eight_d_report,
      # process_routing, capa, quality_report
    dtos/                            # Pydantic context models, one per adapter
      __init__.py
      cert_of_conformance.py
      spc.py
      # future: one per adapter
    services/
      typst_generator.py             # Compiler singleton + compile() wrapper
      registry.py                    # Lazy-loaded adapter list
      pdf_generator.py               # Dispatcher (refactored, no Playwright)
    templates/
      _common/
        page-setup.typ               # Fonts, margins, page header/footer
        palette.typ                  # Shared colors
        tables.typ                   # Standard table styles
        status-badges.typ            # status-badge() function
        metadata.typ                 # Field/value grid helper
        signatures.typ               # Signature block grid
        charts.typ                   # CeTZ chart helpers (SPC etc.)
      cert_of_conformance.typ        # [sprint]
      spc_report.typ                 # [sprint]
    tests/
      base.py                        # ReportAdapterTestMixin (4 free tests per report)
      test_cert_of_conformance.py    # [sprint]
      test_spc.py                    # [sprint]
      test_typst_generator.py        # Smoke test the wrapper itself
      fixtures/                      # Sample context JSON for each report
        cert_of_conformance_sample.json
        spc_sample.json
    management/
      commands/
        export_context.py            # `./manage.py export_context <report> --id=N`
```

### Fonts: Noto via apt

Google's Noto family via Debian's `fonts-noto-core` package. One line
in the Dockerfile, no font files to commit to the repo, no license
audit (Noto is SIL OFL and shipping it in a Debian image is standard
practice).

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl nodejs npm cron \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*
```

`fonts-noto-core` installs Noto Sans, Noto Serif, and Noto Sans Mono
(Latin / Cyrillic / Greek coverage) at `/usr/share/fonts/truetype/noto/`.
Image size impact: ~9 MB.

Typst discovers these via its default system-font scan — no
`fc-cache`, no `font_paths` parameter on the `Compiler`, nothing else
to configure. If Typst can't find a named font, it falls back to its
embedded fonts (Libertinus Serif, New Computer Modern, DejaVu Sans
Mono) — ugly but never fails.

**Template usage:**
```typst
#set text(font: "Noto Serif")            // body
#show heading: set text(font: "Noto Sans")
```

If future customers require a different typeface, drop a `.ttf` into
a new `PartsTracker/fonts/` directory and pass `font_paths=...` to
the `Compiler`. That path is available but unused in the current
plan.

### Typst generator service

Uses the `Compiler` class (not the one-shot `typst.compile()`) so Celery
workers instantiate it once per process and reuse across PDF jobs —
avoids compiler re-initialization on every request.

```python
# Tracker/reports/services/typst_generator.py
import json
import threading
from pathlib import Path

import typst
from django.conf import settings

TEMPLATES_DIR = Path(settings.BASE_DIR) / "Tracker" / "reports" / "templates"

_compiler = None
_compiler_lock = threading.Lock()


def get_compiler() -> typst.Compiler:
    """
    Process-wide Compiler, initialized lazily on first compile.
    Thread-safe via double-checked locking (matters for threaded Celery
    pools; prefork workers each get their own Compiler at no cost).
    Lazy init is also fork-safe — Celery prefork forks before first
    compile, so the Compiler is created post-fork per worker process.
    """
    global _compiler
    if _compiler is None:
        with _compiler_lock:
            if _compiler is None:  # double-check under lock
                _compiler = typst.Compiler()
    return _compiler


def generate_typst_pdf(template_name: str, context: dict) -> bytes:
    """
    Compile a template to PDF bytes.

    Template imports (e.g. `_common/page-setup.typ`) resolve relative to
    the template file. Universe packages resolve from the vendored
    cache at /root/.cache/typst/packages/ (copied in via Dockerfile).
    """
    template_path = TEMPLATES_DIR / template_name
    return get_compiler().compile(
        input=str(template_path),
        format="pdf",
        sys_inputs={"data": json.dumps(context, default=str)},
    )
```

Templates read the context at the top via:
```typst
#let data = json(sys.inputs.at("data"))
```

### Adapter base class contract

```python
from typing import ClassVar
from pydantic import BaseModel
from rest_framework import serializers

class ReportAdapter:
    name: ClassVar[str]                          # Stable registry key
    title: ClassVar[str]                         # Human-readable (filenames, emails)
    template_path: ClassVar[str]                 # Path under templates/
    context_model_class: ClassVar[type[BaseModel]]   # Pydantic model
    param_serializer_class: ClassVar[type[serializers.Serializer]]
    classification_default: ClassVar[str] = "INTERNAL"

    def build_context(self, validated_params, user, tenant) -> BaseModel:
        """
        Query Django ORM, return a Pydantic instance (NOT a dict).
        The dispatcher calls .model_dump(mode='json') before passing
        to Typst, so this method just returns the typed object.
        """
        raise NotImplementedError

    def get_filename(self, validated_params, context: BaseModel) -> str:
        return f"{self.name}_{validated_params.get('id', 'unknown')}.pdf"
```

Timeouts (30s soft / 60s hard) live on the `RetryableTypstTask`
Celery base class — they apply uniformly to every report. If SPC or
some future report proves genuinely slower, add a per-report override
at that point; don't expose configurability we don't need.

### Per-adapter implementation pattern

Each adapter is four files totaling ~250 lines:

| File | Purpose | Approx lines |
|------|---------|--------------|
| `adapters/<name>.py` | Adapter class + param serializer | ~80 |
| `dtos/<name>.py` | Pydantic context model(s) | ~40 |
| `templates/<name>.typ` | Typst template | ~100-250 |
| `tests/test_<name>.py` | Subclass of `ReportAdapterTestMixin` | ~30 |
| `tests/fixtures/<name>_sample.json` | Sample context fixture | N/A |

The render-test mixin (`tests/base.py`) provides four free tests per
report by subclassing:

```python
class ReportAdapterTestMixin:
    adapter_class: type[ReportAdapter]
    fixture_name: str

    def test_context_validates_against_model(self): ...
    def test_template_compiles_to_pdf(self): ...
    def test_output_is_deterministic(self): ...
    def test_cross_tenant_id_is_rejected(self): ...

# per report:
class TestCertOfConformance(ReportAdapterTestMixin, TestCase):
    adapter_class = CertOfConformanceAdapter
    fixture_name = "cert_of_conformance_sample"
```

### New DRF patterns

Replace `GenerateReportSerializer.params = DictField()` with a
type-routed serializer that dispatches to the adapter's
`param_serializer_class`:

```python
class GenerateReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=...)
    params = serializers.JSONField()

    def validate(self, data):
        adapter = get_adapter(data['report_type'])
        ps = adapter.param_serializer_class(
            data=data['params'],
            context=self.context,
        )
        ps.is_valid(raise_exception=True)
        data['validated_params'] = ps.validated_data
        return data
```

---

## What Gets Ported

Each existing report type becomes a Typst adapter + template pair.

### SPC Report

**Current:** `SpcPrintPage.tsx` uses mock data, rendered via Recharts,
converted to PDF via Playwright.

**Target:** `spc_report.typ` template using CeTZ for X-bar/R, I-MR, and
histogram charts. `SpcAdapter.build_context()` calls the existing SPC
service methods that power `/api/spc/data/`, `/api/spc/capability/`,
`/api/spc/baselines/active/`.

**Effort:** 2-3 days. CeTZ chart prototyping is the bulk of the work.
Prototype already completed for X-bar + R — needs I-MR, histogram, and
real-data wiring.

**Files deleted:**
- `ambac-tracker-ui/src/pages/SpcPrintPage.tsx`
- SPC entry in `REPORT_CONFIG` dict

### CAPA Report

**Current:** `CapaPrintPage.tsx` fetches via `api.api_capas_retrieve`,
renders HTML, Playwright to PDF.

**Target:** `capa_report.typ` with structured 8D-lite layout.
`CapaAdapter.build_context()` serializes the CAPA, related RcaRecord
(FiveWhys/Fishbone), CapaTasks, and CapaVerification.

**Effort:** 1-2 days.

**Files deleted:**
- `ambac-tracker-ui/src/pages/CapaPrintPage.tsx`

### Quality Report

**Current:** `QualityReportPrintPage.tsx` with inspection findings table.

**Target:** `quality_report.typ`.

**Effort:** 1 day.

**Files deleted:**
- `ambac-tracker-ui/src/pages/QualityReportPrintPage.tsx`

---

## What Gets Added (new reports, Tier 1 PDF backlog)

These are the five Tier 1 PDFs from `PDF_EXPORTS_REQUIREMENTS.md` that
have not yet been built. All are Typst-native from day one.

| Report | Source data | Template complexity | Effort |
|--------|-------------|--------------------|--------|
| Certificate of Conformance | Order + Parts + QualityReports | Low — single page form | 1-2 days |
| Part Traveler | Part + StepTransitionLog + attributions | Medium — per-step history | 1-2 days |
| NCR Report | QuarantineDisposition + QualityReports | Medium — structured form | 1-2 days |
| FAI Form 3 (Dimensional) | MeasurementDefinition + MeasurementResult | Medium — measurement table | 2 days |
| 8D Report | CAPA + RcaRecord + CapaTasks + CapaVerification | High — 8 sections, multi-page | 2-3 days |

Plus the process-routing report (prototyped during planning):

| Report | Source data | Effort |
|--------|-------------|--------|
| Process Routing | Processes + ProcessStep + StepEdge | 1-2 days (prototype done) |

Total new report work: **~10-15 days**.

---

## What Gets Removed

### Python packages

```diff
- playwright==1.57.0
```

### Dockerfile changes

Remove any `playwright install --with-deps chromium` step and
associated apt packages.

```diff
- RUN apt-get install -y libgbm1 libnss3 libatk-bridge2.0 libxcomposite1 ...
- RUN playwright install --with-deps chromium
```

(Note: the current Dockerfile never installed these, but the intent
was to add them before first Playwright deploy. Now they never need
to be added.)

### Backend code

- `Tracker/reports/services/pdf_generator.py` — rewrite stripped down.
  Remove:
  - `_browser`, `_playwright`, `_browser_lock`, `_request_count` globals
  - `MAX_REQUESTS_PER_BROWSER` constant
  - `CHROMIUM_ARGS` constant
  - `_launch_browser()`, `_shutdown_browser_internal()`, `get_browser()`
  - `shutdown_browser()` public function
  - `PdfGenerator.REPORT_CONFIG` dict (replaced by adapter registry)
  - Playwright imports and browser-context creation in `generate()`

- `PartsTrackerApp/celery_app.py` — remove `worker_shutdown` signal
  handler for browser cleanup:

  ```diff
  - @worker_shutdown.connect
  - def cleanup_browser(**kwargs):
  -     from Tracker.reports.services.pdf_generator import shutdown_browser
  -     shutdown_browser()
  ```

- `Tracker/management/commands/generate_pdf.py` — rewrite to call
  Typst adapter directly instead of Playwright. Remove `--screenshot`
  option; add `--save-typst-source` option for debugging.

### Frontend code

- Delete `SpcPrintPage.tsx`
- Delete `CapaPrintPage.tsx`
- Delete `QualityReportPrintPage.tsx`
- Remove the three print routes from `router.tsx`
- `useReportEmail.ts` — `ReportType` union stays the same
  (report type names don't change), no code changes

### Infrastructure

- Remove Playwright-specific memory overhead from Railway service
  specs. Backend and celery-worker can drop from 1 GB to 512 MB per
  service (subject to load testing).

### Abandoned security work

Work that was on the roadmap to make Playwright safe, now unnecessary:

- Signed URL token generation and validation module
- Session cookie forwarding to Playwright browser context
- Per-request tenant-scoped auth for frontend print routes
- Subprocess-to-HTTP tenant context propagation

---

## Infrastructure Changes

### Dockerfile

**Before:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential libpq-dev curl nodejs npm cron
# (Playwright deps would have been added here)
```

**After:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl nodejs npm cron \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

# Vendored Typst Universe packages (cetz, diagraph) — works offline,
# required for on-prem deployments behind corporate firewalls.
COPY PartsTracker/typst_packages /root/.cache/typst/packages/

# requirements.txt swaps `playwright` → `typst==0.14.8` and adds
# `pydantic>=2.13` explicitly.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

Image size impact:
- `fonts-noto-core`: +9 MB
- Vendored Typst packages: +5-10 MB
- Removed Chromium (was never installed in the current Dockerfile,
  but was planned to be): -400 MB

Net image delta vs. "Dockerfile with Playwright added in": ~-380 MB.

### Typst Universe package vendoring

On-prem deployments behind corporate firewalls cannot reach Typst
Universe at runtime, so all `@preview/...` packages must be vendored
in the image. Railway deployments get the same benefit:
deterministic builds, no dependency on Typst Universe being up.

**Adding a new package:**

1. On a connected dev machine, compile a template that imports it:
   ```typst
   #import "@preview/newpkg:1.2.3": *
   ```
2. Typst caches it at `~/.cache/typst/packages/preview/newpkg/1.2.3/`.
3. Copy that directory into the repo:
   ```
   cp -r ~/.cache/typst/packages/preview/newpkg \
         PartsTracker/typst_packages/preview/
   ```
4. Commit. Next Docker build includes the package.

**Initial set for the sprint:**
- `cetz@0.3.2` — drawing primitives and charts (required for SPC)
- `cetz-plot@0.1.1` — plot helpers for cetz
- `diagraph@0.3.0` — Graphviz-based DAG rendering (for future process
  routing report; vendored now so it's ready)

### Railway configuration

- No environment variable changes needed.
- Memory tier may be reducible after launch (test first). Rough
  expectation: Backend and celery-worker can drop from 1 GB to 512 MB
  per service. Combined monthly cost reduction: ~$10-15.

---

## Testing Strategy

### Unit tests per adapter

For each adapter:

1. **Param validation tests** (`test_{name}.py::ValidationTests`)
   - Valid params for user's tenant → pass
   - Valid params for another tenant → 404 / validation error
   - Missing required params → validation error
   - Extra params → ignored or rejected (adapter's choice)

2. **Context building tests** (`test_{name}.py::ContextTests`)
   - `build_context()` returns JSON-serializable dict
   - Tenant scoping enforced in ORM queries
   - All template-referenced keys present in returned dict

3. **Rendering smoke tests** (`test_{name}.py::RenderTests`)
   - Given a known context dict, `typst.compile()` succeeds
   - Output is non-empty bytes starting with `%PDF-`
   - Output is deterministic (byte-identical on re-run)

### Cross-cutting tests (`test_param_validation.py`)

- Every adapter's param serializer rejects cross-tenant IDs
- Every adapter handles missing user context gracefully
- Every adapter's context dict is JSON-serializable

### Load testing (pre-production)

- Generate 100 PDFs of each type concurrently via Celery
- Verify peak memory stays under service allocation
- Verify no leaked file handles / subprocess creeps

---

## Migration Sequence

Dependency-ordered. With no production users, the full cutover
happens in one PR — no parallel running, no per-phase deploy
pressure, no rollback-to-Playwright safety net needed.

### Phase 0: Infrastructure (1 day)

**Goal:** Typst works end-to-end with a "hello world" PDF, locally
and on Railway.

- [ ] Add `typst==0.14.8` and `pydantic>=2.13` to `requirements.txt`
- [ ] Vendor Typst Universe packages to `PartsTracker/typst_packages/preview/`:
      - `cetz/0.3.2/`, `cetz-plot/0.1.1/`, `diagraph/0.3.0/`
- [ ] Update Dockerfile:
      - `fonts-noto-core` in the apt install line
      - `COPY PartsTracker/typst_packages /root/.cache/typst/packages/`
- [ ] Create `Tracker/reports/services/typst_generator.py` with the
      `Compiler` singleton + `threading.Lock` double-check pattern
- [ ] Create `Tracker/reports/templates/_common/page-setup.typ` with
      Noto Sans headings / Noto Serif body, margins, page header/footer
- [ ] Create `Tracker/reports/templates/hello_world.typ` that imports
      `_common/page-setup.typ` and renders a test document exercising
      both Noto fonts and a `@preview/cetz` import (verifies both the
      font install and the vendored-packages copy)
- [ ] Write `Tracker/reports/tests/test_typst_generator.py`:
  - Generates PDF bytes, asserts first 4 bytes are `%PDF`
  - Asserts PDF size > 500 bytes (catches empty output)
  - Runs twice, asserts byte-identical output (determinism check)
- [ ] Deploy to Railway; run the smoke test on the live container via
      `railway run --service Backend python manage.py shell`

**Exit criteria:**
- `typst_generator.generate_typst_pdf(...)` returns valid PDF bytes
  locally AND on Railway
- Deterministic: two compiles of the same template + context produce
  byte-identical output
- Fonts verified: hello-world PDF visibly uses Noto Sans + Noto Serif
- Vendored packages work: `@preview/cetz` imports without network access

### Phase 1: Framework (2-3 days)

**Goal:** Adapter registry, dispatch logic, Pydantic contract, and
render-test mixin in place. No actual report adapters yet.

- [ ] Create `Tracker/reports/adapters/base.py` with `ReportAdapter`:
      Pydantic `context_model_class`, `soft_timeout_seconds`,
      `hard_timeout_seconds`, `build_context() -> BaseModel`
- [ ] Create `Tracker/reports/services/registry.py` (lazy-loaded list
      of dotted paths, mirror of `integrations/services/registry.py`)
- [ ] Create `Tracker/reports/tasks.py` with `RetryableTypstTask`
      (autoretry on `TimeoutError`, `OSError`, `MemoryError` only)
- [ ] Rewrite `PdfGenerator.generate()` to dispatch through the
      registry: validate params via adapter's param serializer →
      build context → `.model_dump(mode='json')` → compile
- [ ] Wire `settings.DEBUG` into error response verbosity; always
      `logger.exception(...)` regardless
- [ ] Wrap sync `/api/reports/download/` compile call in
      `concurrent.futures` with 30s timeout
- [ ] Create `Tracker/reports/tests/base.py` with
      `ReportAdapterTestMixin` (4 free tests per adapter)
- [ ] Build `_common/` template library: `palette.typ`, `tables.typ`,
      `status-badges.typ`, `metadata.typ`, `signatures.typ` (any that
      aren't already in `page-setup.typ`)
- [ ] Create `Tracker/reports/management/commands/export_context.py`
      for dumping adapter output to JSON (template dev workflow)
- [ ] Write a dummy `TestReportAdapter` that exercises the full path

**Exit criteria:** Dummy adapter renders a PDF through the full
pipeline. Per-adapter Pydantic validation and tenant scoping both
work. `ReportAdapterTestMixin` gives a new report 4 passing tests with
minimal boilerplate.

### Phase 2: Build CofC + SPC (4-6 days)

**Goal:** Two reports shipped, Playwright removed. Framework validated
against both a simple (form + table) and complex (charts) use case.

**Certificate of Conformance first (~2 days):**

CofC field list (the Pydantic model's shape; deliberately conservative —
add customer-specific variants later as requests come in):

| Field | Source | Notes |
|-------|--------|-------|
| `certificate_number` | `f"CoC-{order.id}"` | Generated on render, sequential by order |
| `issue_date` | `GeneratedReport.generated_at` (date only) | Pinned from the audit record, not `date.today()`, for regeneration stability |
| `customer_name` | `order.customer.name` | Falls back to `order.company.name` if no direct customer FK |
| `customer_po_number` | `order.customer_po_number` or similar | TBD — check `Orders` model; add field if missing |
| `part_number` | `part_type.ID_prefix + part_type.ERP_id` | Standard format |
| `part_type_name` | `part_type.name` | Human-readable |
| `revision` | `part_type.version` or similar | From SecureModel version chain |
| `quantity` | `order.parts.count()` | Released parts only (`status='RELEASED'`) |
| `serial_range` | `min(p.serial)` → `max(p.serial)` | Lexicographic on the serial strings |
| `parts` | List of `PartLine` DTOs (serial, status, key measurements if any) | Keep to ≤50 rows inline; larger batches summarized |
| `material_lot` | First `MaterialLot` linked to the order | Or list of lots if multiple |
| `process_name` | `order.process.name` | Including version |
| `process_version` | `order.process.version` | |
| `inspection_standard` | Hardcoded to `"INS-<part_type_id>-F"` or TBD | Product decision — may need per-part-type field |
| `qc_signatory_name` | `order.qa_approver.get_full_name()` | TBD — check if Orders has QA approver FK |
| `qc_signatory_date` | `order.qa_approved_at` | Ditto |
| `itar_controlled` | `part_type.itar_controlled` | Drives a "ITAR Controlled — Export Restricted" stamp |
| `eccn` | `part_type.eccn` | Shown in metadata grid |
| `tenant_name` | `tenant.name` | For the document header |
| `tenant_logo_ref` | None for v1 | Per-tenant branding deferred |

Fields marked "TBD" may require a small Orders model addition or a
product decision before the adapter can build the context. **Resolve
those before starting the CofC adapter** — otherwise Day 1 becomes
design work, not implementation. Worst case: hardcode a placeholder
with a `# TODO: product decision` comment and move on.

- [ ] Confirm Orders model has (or add) `customer_po_number`, QA
      approver FK, approval timestamp — else hardcode
- [ ] `dtos/cert_of_conformance.py` — Pydantic model per above
- [ ] `adapters/cert_of_conformance.py` — param serializer + adapter
- [ ] `templates/cert_of_conformance.typ` — uses shared `_common/`
- [ ] `tests/test_cert_of_conformance.py` — 4 tests via mixin + any
      report-specific edge cases (large parts list truncation, ITAR
      stamp rendering)
- [ ] `tests/fixtures/cert_of_conformance_sample.json`
- [ ] Register in `REPORT_ADAPTERS` list

Used to prove the framework and shake out issues. Any adjustments to
the base class / mixin / `_common/` library happen during this report.

**SPC second (~2-3 days):**
- [ ] `dtos/spc.py` — Pydantic model for subgroups, control limits,
      capability stats
- [ ] `adapters/spc.py` — calls existing SPC service methods that back
      `/api/spc/*` endpoints
- [ ] `templates/_common/charts.typ` — CeTZ helpers for X-bar/R, I-MR,
      histogram with OOC overlay
- [ ] `templates/spc_report.typ` — uses shared `_common/` + charts
- [ ] `tests/test_spc.py` — 4 tests via mixin
- [ ] `tests/fixtures/spc_sample.json`
- [ ] Register in `REPORT_ADAPTERS` list

Validates that CeTZ can handle the one genuinely new rendering need.

**Remove Playwright:**
- [ ] Remove `playwright` from `requirements.txt`
- [ ] Delete all Playwright imports and code from `pdf_generator.py`
- [ ] Remove `worker_shutdown` browser cleanup signal
- [ ] Delete `REPORT_CONFIG` dict
- [ ] Rewrite `generate_pdf` management command for Typst
- [ ] Delete `SpcPrintPage.tsx`, `CapaPrintPage.tsx`,
      `QualityReportPrintPage.tsx` from the frontend
- [ ] Update `Documents/PDF_EXPORTS_REQUIREMENTS.md` and
      `Documents/PRINT_SYSTEM_UI_PLAN.md` to describe the Typst flow

Not ported during the sprint:
- `capa`, `quality_report` Playwright reports — not required for
  launch; delete their Playwright configs but defer Typst versions
  until a real user needs them
- All other Tier 1 PDFs (Part Traveler, NCR, FAI, 8D, Process Routing)
  — defer until actually needed

**Exit criteria:** Codebase has zero references to Playwright. Each
shipping report type has an adapter + template + tests. Docker image
is ~400 MB smaller than the Playwright-era plan called for (and in
reality, matches what you actually deployed since Playwright never
made it to production).

---

## Risk Assessment

Pre-launch context: no customer impact if something breaks, no
regulatory obligations inherited from prior output, no back-compat
requirements.

### Items worth paying attention to

1. **CeTZ chart work if SPC is in scope.** The chart-heavy report is
   the one area with real unknowns — OOC point overlay, legend
   placement, multi-chart layout. Prototype in typst.app before
   committing to CeTZ for SPC. Sample X-bar + R prototype from
   planning already renders cleanly. If SPC isn't needed at launch,
   skip this risk entirely by deleting the report type.

2. **Compile timeout.** Unlike Playwright's explicit timeouts, Typst
   has none by default. A runaway template hangs a Celery worker.
   Wrap `Compiler.compile()` in a hard timeout (Celery `time_limit`
   or `signal.alarm`). Decide the number before Phase 1.

3. **Concurrency model.** `typst.Compiler` reuse across Celery workers
   depends on pool mode. Prefork: one Compiler per process via lazy
   init, no locking needed. Threads: shared Compiler needs a lock.
   Gevent: untested — verify or switch to prefork.

4. **Template ↔ context drift.** Adapter returns a dict, template
   reads keys from it. Without a shared contract, adding a field to
   one side and not the other produces silent bugs. Pick one of:
   typed DTOs, JSON Schema files, or strict unit tests.

### Low risk

5. **Typst version churn (v0.14.8 as of Feb 2026).** Active
   development; breaking changes possible between minor versions.
   Pin exact version. Upgrade deliberately.

6. **Font rendering.** Typst scans system font directories by default;
   `fonts-noto-core` installs to `/usr/share/fonts/truetype/noto/`
   where Typst will find it. If the scan misses (unexpected in a
   Debian-based image but possible in other runtimes), Typst falls
   back to embedded fonts (Libertinus Serif, New Computer Modern,
   DejaVu Sans Mono) — output is ugly but renders. The `Compiler()`
   constructor accepts an explicit `font_paths=[...]` parameter as a
   fallback if the scan ever fails; not used today. Hello-world test
   in Phase 0 asserts Noto Sans and Noto Serif are actually loading
   (not silent fallback to Libertinus).

7. **manylinux wheel availability.** `typst` provides pre-built
   CPython 3.8+ wheels for manylinux2014. Current Dockerfile uses
   `python:3.12-slim` — confirmed compatible, no Rust toolchain
   needed at install time.

8. **Developer ramp-up on Typst syntax.** 2-3 days to fluency.
   typst.app live preview and VS Code's Tinymist extension make
   iteration fast.

9. **Template DRY.** Without inheritance, headers/footers/styling
   must be shared via `_common/` imports. Typst resolves
   `#import "_common/..."` automatically; just requires discipline.

10. **PDF bytes persistence.** The Celery task already stores generated
    PDFs in the DMS via `Documents.objects.create(...)` + `document.file.save(...)`.
    That stays the same — Typst-generated bytes go through the same
    path. The sync `/api/reports/download/` endpoint streams bytes
    directly back to the client without persisting by default; the
    dialog's "Save to DMS" checkbox opts into the same `Documents`
    record creation pattern. No new persistence layer needed.

---

## Specific Implementation Concerns

Two items that came up in plan review that need explicit handling
during Phase 1 / 2, not just at design time.

### Sync vs. async download coordination

Your `ReportViewSet` exposes two code paths that generate the same PDF:

- `POST /api/reports/generate/` — queues a Celery task, emails the
  PDF when ready, tracked in `GeneratedReport`
- `POST /api/reports/download/` — generates synchronously in the web
  request, streams PDF bytes back immediately

Both will exist after the migration. Two concrete risks to address:

**Risk 1: double-generation.** A user could click "Download" and
"Email me" on the same report in quick succession. Currently, both
paths run independently — two Typst compiles, two `GeneratedReport`
records, possibly two `Documents` rows. Not broken, just wasteful.

*Mitigation:* don't solve this preemptively. It's user-visible as
"two emails arrived" which is annoying but not incorrect. If a real
user complains, add idempotency via a request ID passed from the
frontend. Log the concern, don't fix it in the sprint.

**Risk 2: sync path timeout abandons work.** The sync path's
`concurrent.futures` timeout (30s) raises `TimeoutError` on the web
request but leaves the compile thread running inside the gunicorn
worker. That thread eventually finishes, wastes memory, can't be
cancelled. Over time this degrades the web process.

*Mitigation:* the web worker will eventually be killed by gunicorn's
`max_requests` setting (which you have configured at 2 workers ×
threads per the Dockerfile CMD). Memory gets reclaimed on worker
rotation. Not ideal but bounded.

*Better mitigation (if sync path becomes important):* flip the sync
download path to "enqueue + poll + return when ready" — same Celery
task, but the web request blocks on `AsyncResult.get(timeout=30)`.
Timeout on the web side only affects the HTTP response; the Celery
task runs to completion or hits its own hard time limit and is
killed cleanly. Defer this change until the simple approach causes a
real problem.

Document both risks in code comments on the sync path. Don't build
the coordination infrastructure now.

### SPC service methods and tenant scoping

The SPC adapter's `build_context()` will call the same service
functions that back `/api/spc/data/`, `/api/spc/capability/`, and
`/api/spc/baselines/active/`. Those service methods were written
assuming the caller is a DRF viewset whose `get_queryset()` has
already applied tenant scoping via `TenantScopedMixin`. If the
adapter calls them with raw IDs from the param serializer, the
service methods may not re-check tenant ownership internally —
which would replicate the exact security hole this migration is
supposed to close.

**Action items during Phase 2:**

- [ ] Audit the functions at `Tracker/viewsets/spc.py` (or wherever
      the SPC logic lives): do they accept `process_id`, `step_id`,
      `measurement_id` and trust those IDs, or do they re-filter by
      tenant internally?
- [ ] If they trust IDs: either
      (a) refactor the service methods to accept `tenant` explicitly
          and filter on it, OR
      (b) have the SPC param serializer query tenant-scoped querysets
          (e.g., `Processes.objects.filter(tenant=user.tenant, pk=value).first()`)
          and pass the actual model instances (not IDs) to the
          service methods
- [ ] Option (b) is cheaper for the sprint; option (a) is better
      long-term
- [ ] Add a test: construct an SPC report request with a
      `process_id` from another tenant, assert 404/validation error

**Same check applies to the CofC adapter.** It queries `Orders` and
`Parts` directly. Make sure every ORM query in `build_context()`
filters by tenant at the query level, never relies on "the caller
validated this ID already." The param serializer validates that the
Order exists in the tenant; the adapter's ORM calls need to filter
by tenant independently as a defense-in-depth measure.

The `ReportAdapterTestMixin.test_cross_tenant_id_is_rejected` is the
enforcement mechanism. Make sure that test actually probes the ORM
path, not just the param serializer.

---

## Per-Phase Effort Summary

| Phase | Work | Effort |
|-------|------|--------|
| 0 | Infrastructure + hello-world | 1 day |
| 1 | Framework (base class, mixin, `_common/`, registry, timeouts) | 2-3 days |
| 2 | Build CofC + SPC, remove Playwright | 4-6 days |
| **Total** | | **7-10 days** |

Subsequent reports (Part Traveler, NCR, FAI, 8D, Process Routing,
future CAPA / QualityReport / ad-hoc customer requests) are expected
to take ~1-2 days each because the framework + `_common/` library +
CeTZ chart helpers are all in place after the sprint.

---

## Decisions Made

All 8 decision points have been resolved. Each is reflected in the
infrastructure, adapter base class, or Dockerfile above.

| # | Question | Answer |
|---|----------|--------|
| 1 | Context schema | Pydantic model per adapter (`dtos/<name>.py`). Adapter returns Pydantic instance; dispatcher calls `.model_dump(mode='json')` before passing to Typst. `ReportAdapterTestMixin` provides a render test per template as enforcement. |
| 2 | Compile timeout | 30s soft / 60s hard. Enforced via Celery `soft_time_limit` / `time_limit` on `RetryableTypstTask` base. Sync `/api/reports/download/` wraps the compile call in `concurrent.futures` with matching 30s timeout. Both values are class attributes on `ReportAdapter` and may be overridden per report. |
| 3 | Celery concurrency | Prefork (current default, no config change). Lazy `Compiler` singleton with `threading.Lock` double-check pattern — the lock is a safety belt if the pool mode ever changes; in prefork each worker process gets its own Compiler with no contention. |
| 4 | Universe packages | Vendored in `PartsTracker/typst_packages/`, copied to `/root/.cache/typst/packages/` in the Dockerfile. No runtime or build-time network calls to Typst Universe. Works for both Railway and on-prem-behind-firewall deployments. |
| 5 | Error surfacing | Verbose Typst error messages gated by `settings.DEBUG`. Real exception always logged server-side via `logger.exception`. Template compile errors do NOT retry; `RetryableTypstTask.autoretry_for` only covers transient errors (`TimeoutError`, `OSError`, `MemoryError`). |
| 6 | Reports in sprint scope | **Certificate of Conformance** (built first — simplest exemplar, establishes framework) then **SPC Report** (built second — validates CeTZ chart handling). All other reports deferred until real need surfaces. |
| 7 | Fonts | `fonts-noto-core` apt package in Dockerfile. Templates use Noto Sans for headings, Noto Serif for body. No `.ttf` files committed to repo. Typst's embedded fallbacks (Libertinus Serif, New Computer Modern, DejaVu Sans Mono) handle edge cases. |
| 8 | Sequencing | Tight sprint: Phase 0 + framework + CofC + SPC consecutively, ~7-9 days of focused work. No parallel running or phased rollout (nothing live to preserve). |

---

## References

### Internal docs

- `Documents/PDF_EXPORTS_REQUIREMENTS.md` — full Tier 1 / Tier 2 PDF catalog
- `Documents/PRINT_SYSTEM_UI_PLAN.md` — existing frontend dialog +
  print page infrastructure
- `Documents/RAILWAY_DEPLOYMENT.md` — deployment configuration reference
- Current Playwright implementation: `Tracker/reports/services/pdf_generator.py`

### Typst ecosystem

- [Typst documentation](https://typst.app/docs/) — language and standard library
- [typst on PyPI](https://pypi.org/project/typst/) — Python package (v0.14.8)
- [typst-py GitHub (messense)](https://github.com/messense/typst-py) —
  Python binding source, API reference
- [typst-py readthedocs](https://typst-py.readthedocs.io/en/latest/) —
  `Compiler` class docs, `font_paths` parameter
- [CeTZ — charts/drawing](https://typst.app/universe/package/cetz)
- [diagraph — Graphviz via WASM](https://typst.app/universe/package/diagraph)

### Railway + Docker

- [Railway Dockerfile guide](https://docs.railway.com/builds/dockerfiles)
- Note: the [Typst Compiler API template](https://railway.com/deploy/fFq3fV)
  on Railway exists but is flagged not-production-ready by its creator.
  We use the `typst` pip package directly inside our own Django/Celery
  processes — no separate service.

---

## Appendix: Why Not Hybrid

An earlier version of this plan kept Playwright for SPC reports only
("SPC charts are harder to migrate"). After review, this was rejected:

- Keeping two engines means twice the deployment complexity, testing
  burden, and "why did this PDF fail" debugging surface.
- Railway cost benefit requires removing Chromium entirely — partial
  migration saves nothing.
- Security benefit requires eliminating the Playwright attack surface
  — one unauthenticated endpoint is the same risk as three.
- CeTZ for SPC charts is a 2-3 day problem, not a multi-week one.
  Prototype work already validated the approach.

Full migration. No fallback.