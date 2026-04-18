# Print & Label System - UI Plan

**Last Updated:** April 2026

Covers the generate/print dialog, label components, and the two initial verticals: part labels and SPC print page. For PDF infrastructure details, see `PDF_EXPORTS_REQUIREMENTS.md`. For label design decisions, see `WO_MANAGEMENT_FEATURE_MATRIX.md` Bucket 1.

---

## Standardized System

Every printable/generatable document in the app follows the same pattern. This section defines the standard so new document types are trivial to add.

### The Pattern (for any new document/label type)

**Backend (one config entry):**
```python
# In Tracker/services/pdf_generator.py → REPORT_CONFIG
"my_new_document": {
    "route": "/my-thing/{id}/print",
    "wait_selector": "[data-print-ready]",
    "title": "My Document",
    "timeout": 15000,
    # Optional overrides (omit for default Letter with 0.5in margins):
    "page": {"format": "Letter"},
    "margin": {"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
    "needs_scroll": False,
}
```

**Frontend (three files):**

1. **Print page component** (`src/pages/MyDocumentPrintPage.tsx`):
   - Fetches its own data via existing hooks
   - Wraps in `<PrintLayout>` for documents, bare `<div data-print-ready>` for labels
   - Sets `data-print-ready` only after all data is loaded and rendered

2. **Route** (`src/router.tsx`):
   ```tsx
   export const myDocumentPrintRoute = createRoute({
     getParentRoute: () => rootRoute,
     path: '/my-thing/$id/print',
     component: lazyRouteComponent(() => import("@/pages/MyDocumentPrintPage")),
   })
   ```

3. **Trigger button** (on the relevant detail/list page):
   ```tsx
   <GenerateDocumentDialog
     reportType="my_new_document"
     params={{ id: item.id }}
     title={`My Document for ${item.name}`}
     defaultSaveToDms={true}
   />
   ```

That's it. The dialog handles download/email/DMS. The PDF generator handles rendering. The audit trail handles logging. No other wiring needed.

### Adding a New Label Type

Same pattern but with page size overrides and no `PrintLayout`:

```python
"my_label": {
    "route": "/labels/my-thing/print",
    "wait_selector": "[data-print-ready]",
    "title": "My Label",
    "timeout": 10000,
    "page": {"width": "4in", "height": "2in"},
    "margin": {"top": "0", "bottom": "0", "left": "0", "right": "0"},
},
```

For sheet labels (multiple labels per page), use Letter format with Avery-specific margins and a CSS grid layout in the print page component.

---

## Prerequisites

**NPM packages to install (not currently in project):**
- `qrcode.react` — QR code SVG rendering
- `jsbarcode` — Code 128 barcode rendering

**Existing infrastructure (already built):**
- `Tracker/services/pdf_generator.py` — warm browser, config-driven, LLM guide comments
- `Tracker/viewsets/reports.py` — `/api/reports/download/` (sync) and `/api/reports/generate/` (async email)
- `ambac-tracker-ui/src/hooks/useReportEmail.ts` — `downloadReport()` and `requestReport()`
- `ambac-tracker-ui/src/components/print-layout.tsx` — shared document wrapper
- SPC hooks exist: `useSpcHierarchy`, `useSpcData`, `useSpcCapability`, `useSpcActiveBaseline`
- Traveler data exists: `api_Parts_traveler_retrieve()` at `GET /api/Parts/{id}/traveler/`

---

## Generate Dialog Component

Reusable dialog for all document/label generation across the app. Replaces individual "Email Report" / "Download" buttons with a unified flow.

### Component: `<GenerateDocumentDialog>`

**Pattern:** Self-contained trigger button using shadcn `Dialog` + `DialogTrigger`. Parent just renders the component; dialog manages its own open state internally.

**Props:**
```tsx
interface GenerateDocumentDialogProps {
  reportType: string;          // REPORT_CONFIG key
  params: Record<string, any>; // passed to the report route
  title: string;               // e.g., "Part Labels for WO-2026-0045"
  defaultSaveToDms?: boolean;  // default true for documents, false for labels
  trigger?: ReactNode;         // custom trigger button (defaults to a "Generate" button)
}
```

**Usage:**
```tsx
<GenerateDocumentDialog
  reportType="part_label_sheet"
  params={{ woId: workOrder.id }}
  title={`Part Labels for ${workOrder.wo_number}`}
  defaultSaveToDms={false}
  trigger={<Button variant="outline"><Printer className="w-4 h-4 mr-2" />Print Labels</Button>}
/>
```

**Layout:**
```
┌─────────────────────────────────────────────┐
│  Generate: Part Labels for WO-2026-0045     │
│─────────────────────────────────────────────│
│                                             │
│  Delivery:                                  │
│  ☑ Download                                 │
│  ☐ Email to me (user@company.com)           │
│  ☐ Email to... [_________________________]  │
│                                             │
│  Save to Documents:                         │
│  ☐ Save to DMS                              │
│     Classification: [Internal ▼]            │
│                                             │
│  [Cancel]                    [Generate]      │
└─────────────────────────────────────────────┘
```

**Classification dropdown values** (from `Documents.ClassificationLevel`):
- PUBLIC — Public
- INTERNAL — Internal Use (default)
- CONFIDENTIAL — Confidential
- RESTRICTED — Restricted
- SECRET — Secret

**Behavior:**
- At least one delivery option must be selected (download, email to me, or email to other)
- "Download" calls `POST /api/reports/download/` → triggers browser file download
- "Email to me" calls `POST /api/reports/generate/` with user's email → async Celery task
- "Email to..." calls same endpoint with custom email address
- "Save to DMS" is independent — if checked, the generated PDF gets stored as a Document record linked to the source entity
- Classification dropdown only shows when "Save to DMS" is checked
- All three (download + email + DMS) can happen from one click of "Generate"
- Loading state on Generate button with spinner while download is in progress
- Toast notification on success: "Labels downloaded" / "Report emailed to..." / "Saved to documents"

### API Changes Needed

**Current state:**
- `useReportEmail.ts` exposes `downloadReport()` and `requestReport()` but neither supports custom recipients or DMS save
- `/api/reports/download/` returns PDF bytes directly, does NOT create a Documents record
- `/api/reports/generate/` sends to authenticated user's email only, DOES create a Documents record via Celery task

**Changes to `/api/reports/download/` (Tracker/viewsets/reports.py):**
- Accept optional `save_to_dms: boolean` and `classification: string` in request body
- When `save_to_dms=true`, create a Documents record (same pattern as the Celery task at `Tracker/tasks.py` ~line 1540) and return the document ID in a response header

**Changes to `/api/reports/generate/` (Tracker/viewsets/reports.py):**
- Accept optional `email_to: string[]` for custom recipients (in addition to or instead of authenticated user)
- Accept optional `save_to_dms: boolean` (currently always saves; make it controllable, default true)
- Accept optional `classification: string` (currently hardcoded to INTERNAL)

**Changes to `useReportEmail.ts`:**
- Extend both functions to accept options object:
  ```tsx
  downloadReport(reportType, params, { saveToDms?: boolean, classification?: string })
  requestReport(reportType, params, { emailTo?: string[], saveToDms?: boolean, classification?: string })
  ```

### Where the Dialog Gets Used

| Location | Trigger Button | Report Type | Default DMS |
|----------|---------------|-------------|-------------|
| WO detail page header | "Print Labels" | `part_label_sheet` | Off |
| WO detail page header | "Generate Traveler" | `wo_traveler_package` | On |
| Parts table action cell | "Print Label" (single) | `part_label_single` | Off |
| Order detail page | "Generate CoC" | `certificate_of_conformance` | On |
| CAPA detail page | "Generate 8D" | `capa_8d_report` | On |
| SPC page | "Print / Export" | `spc` | On |
| NCR detail page | "Generate NCR Report" | `ncr_report` | On |
| Quality report detail | "Generate Report" | `quality_report` | On |

**Note:** There is no dedicated Part Detail page. Part labels are triggered from:
- The WO detail page (batch: all parts in WO)
- Parts table action cells (single: one part at a time, via dropdown or button in `EditPartActionsCell` or similar)

---

## Vertical 1: Part Labels

### Label Component: `<PartLabel>`

Single label for one part. Used both in batch sheets and individual prints.

```tsx
interface PartLabelProps {
  serialNumber: string;
  partTypeName: string;
  partNumber: string;    // part type ID prefix + number
  workOrderNumber: string;
  revision?: string;
  date: string;
  qrValue: string;       // serial number string for QR
  barcodeValue: string;   // serial number string for Code 128
}
```

**Layout (2" × 1" Avery 5160 cell):**
```
┌─────────────────────────────────┐
│ [QR]  TENANT_NAME               │
│       PN: INJ-2500-A            │
│       SN: INJ-2025-0847         │
│       WO: WO-2025-0123          │
│       Rev: C    2026-03-23      │
│ ████████████████████████████    │  ← Code 128
└─────────────────────────────────┘
```

**Libraries (must install):**
- `qrcode.react` — `<QRCodeSVG>` for QR code rendering (`npm install qrcode.react`)
- `jsbarcode` — via a thin React wrapper or `<svg>` ref for Code 128 (`npm install jsbarcode`)

**For batches of 500+:** QR codes pre-rendered server-side as base64 PNG data URIs via Python `qrcode` library, passed as props. Threshold configurable but default to client-side rendering (fast enough for typical WO sizes of 10-100 parts).

### Print Page: `PartLabelPrintPage`

**Route:** `/labels/part/print?ids=1,2,3,...&woId=123`

**Behavior:**
1. Parse `ids` from query params (comma-separated part IDs) or `woId` to fetch all parts for a WO
2. Fetch part data from API: serial number, part type, WO number, revision
3. Render labels in a CSS grid matching Avery 5160 layout (3 columns × 10 rows = 30 per page)
4. Set `data-print-ready` after all labels + QR codes have rendered
5. No `PrintLayout` wrapper — labels don't need the document header/timestamp

**CSS for Avery 5160 (30-up on Letter):**
```css
@page {
  size: letter;
  margin: 0.5in 0.19in;  /* Avery 5160 sheet margins */
}
.label-grid {
  display: grid;
  grid-template-columns: repeat(3, 2.625in);
  grid-auto-rows: 1in;
  gap: 0;
}
.label-cell {
  width: 2.625in;
  height: 1in;
  overflow: hidden;
  padding: 0.05in;
  font-size: 7pt;
}
```

**REPORT_CONFIG entries:**
```python
"part_label_sheet": {
    "route": "/labels/part/print",
    "wait_selector": "[data-print-ready]",
    "title": "Part Labels",
    "timeout": 15000,
    "page": {"format": "Letter"},
    "margin": {"top": "0.5in", "bottom": "0.5in", "left": "0.19in", "right": "0.19in"},
},
"part_label_single": {
    "route": "/labels/part/print",
    "wait_selector": "[data-print-ready]",
    "title": "Part Label",
    "timeout": 10000,
    "page": {"width": "2.625in", "height": "1in"},
    "margin": {"top": "0", "bottom": "0", "left": "0", "right": "0"},
},
```

### Performance Expectations

| Parts | Labels | Sheets | Expected Time (warm browser) |
|-------|--------|--------|------------------------------|
| 10 | 10 | 1 | ~0.5s |
| 30 | 30 | 1 | ~0.5-1s |
| 100 | 100 | 4 | ~1-2s |
| 500 | 500 | 17 | ~3-4s (with pre-rendered QR) |

### Data Fetching

Parts can be fetched via existing API: `api_Parts_list({ work_order: woId })` or `api_Parts_list({ id__in: ids })`. Check if the list endpoint supports ID array filtering; if not, fetch individually or add a filter.

### Buttons in Existing UI

**WO Detail Page** (`WorkOrderDetailPage.tsx`):
Currently only has `WorkOrderStatusActions` in the header (line ~143). Add "Print Labels" and "Generate Traveler" buttons alongside status actions. Both open `<GenerateDocumentDialog>`:

- Print Labels: `reportType="part_label_sheet"`, `params={ woId }`, `defaultSaveToDms={false}`
- Generate Traveler: `reportType="wo_traveler_package"`, `params={ woId }`, `defaultSaveToDms={true}`

**Parts Table** (embedded in WO detail and other pages):
Add a "Print Label" action to the part row action cell. Opens dialog with `reportType="part_label_single"`, `params={ ids: [partId] }`.

---

## Vertical 2: SPC Print Page (Wire to Real Data)

### Current State
- `SpcPrintPage.tsx` exists (865 lines)
- Renders X-bar/R, I-MR, histogram, and out-of-control analysis charts
- Uses **mock data** — hardcoded process/step/measurement hierarchy and generated random data points
- Wrapped in `PrintLayout`
- REPORT_CONFIG entry exists: `"spc"` with route `/spc/print` and wait for `.recharts-surface`

### What Already Exists

**SPC API endpoints (built, in `Tracker/viewsets/spc.py`):**
- `GET /api/spc/hierarchy/` — processes → steps → measurements tree
- `GET /api/spc/data/` — measurement results for control charts
- `GET /api/spc/capability/` — Cpk/Ppk calculations
- `GET /api/spc/baselines/` — frozen baselines with control limits
- `GET /api/spc/baselines/active/` — active baseline for a measurement

**SPC hooks (built, in `ambac-tracker-ui/src/hooks/`):**
- `useSpcHierarchy` — fetches hierarchy via `api.api_spc_hierarchy_list()`
- `useSpcData` — fetches measurement data via `api.api_spc_data_retrieve()`
- `useSpcCapability` — fetches Cp/Cpk/Pp/Ppk via `api.api_spc_capability_retrieve()`
- `useSpcActiveBaseline` — manages baselines via `api.api_spc_baselines_*`

**SPC interactive page (built, `SpcPage.tsx`):**
- Already uses the real hooks and API above
- The print page was built first with mock data; the interactive page was wired to real data afterward

**Generated API client (`src/lib/api/generated.ts`) has:**
- `api_spc_hierarchy_list()`
- `api_spc_data_retrieve(queries)`
- `api_spc_capability_retrieve(queries)`
- `api_spc_baselines_list()`, `_active_retrieve(queries)`
- `api_spc_dimensional_results_retrieve(queries)`

### What Needs to Change

This is a data source swap, not a rewrite. The charts, calculations, and layout stay the same.

**1. Replace mock hierarchy with existing hook:**

Delete the `processData` array (~line 85-230) and replace with:
```tsx
const { data: hierarchy, isLoading: hierarchyLoading } = useSpcHierarchy();
```
Map the API response to the component's existing Process/Step/Measurement types. The field names differ between mock and API:

| Mock field | API field |
|-----------|-----------|
| `name` | `label` |
| `tolerancePlus` | `upper_tol` |
| `toleranceMinus` | `lower_tol` |

Write a mapping function (or update the component types to match the API). Every chart calculation that references `tolerancePlus`/`toleranceMinus` will need the field names updated.

**2. Replace mock chart data with existing hook:**

Delete `generateSpcData()` (~line 255) and `generateIMRData()` (~line 291) functions and replace with:
```tsx
const { data: chartData, isLoading: dataLoading } = useSpcData({
  measurementDefinitionId: selectedMeasurement,
  // any other params the hook expects
});
```
Map API response to existing `SubgroupPoint` / `IndividualPoint` types.

**3. Replace mock control limits with baseline hook:**

```tsx
const { data: baseline } = useSpcActiveBaseline(selectedMeasurement);
```
The hook already filters to the active baseline for the given measurement ID. If a frozen baseline exists, use its stored UCL/LCL/CL values. If not, the existing calculation logic in the component serves as fallback.

**4. Replace mock capability with existing hook:**

```tsx
const { data: capability } = useSpcCapability({
  measurementDefinitionId: selectedMeasurement,
});
```

**5. Gate `data-print-ready` on real data:**

```tsx
const allDataReady = hierarchy && chartData && !hierarchyLoading && !dataLoading;

return (
  <PrintLayout title="SPC Report" subtitle={...}>
    {allDataReady ? (
      <div data-print-ready>
        {/* existing chart rendering, unchanged */}
      </div>
    ) : (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="animate-spin" />
      </div>
    )}
  </PrintLayout>
);
```

### What Stays the Same

- All chart rendering logic (X-bar/R, I-MR, histogram, OOC analysis)
- All statistical calculations (means, ranges, control limit formulas)
- PrintLayout wrapper
- Chart layout and styling
- The REPORT_CONFIG entry (`"spc"`)
- The management command for testing (`python manage.py generate_pdf spc`)

### SPC Print Button

The SPC interactive page (`SpcPage.tsx`) likely has an existing print/email button. Update it to use `<GenerateDocumentDialog>`:
- `reportType="spc"`
- `params={ processId, stepId, measurementId, mode }`
- `title="SPC Report — ${processName} / ${stepName} / ${measurementName}"`
- `defaultSaveToDms={true}`

---

## Future Document Types (follow the standard pattern)

Once the dialog and two verticals are working, adding new types follows the standard pattern (one config entry + one print page + one trigger button):

| Document | Config Key | Print Page | Trigger Location |
|----------|-----------|------------|-----------------|
| WO Traveler | `wo_traveler_package` | `TravelerPrintPage.tsx` — uses existing `api_Parts_traveler_retrieve()` | WO detail |
| Certificate of Conformance | `certificate_of_conformance` | `CocPrintPage.tsx` | Order detail |
| 8D Report | `capa_8d_report` | `Capa8dPrintPage.tsx` | CAPA detail |
| FAI Forms (AS9102) | `fai_report` | `FaiPrintPage.tsx` | Part type / WO detail |
| NCR Report | `ncr_report` | `NcrPrintPage.tsx` | NCR detail |
| WO Bin Label | `wo_label` | Reuse label print page with WO layout | WO detail |
| Material Lot Label | `lot_label` | Reuse label print page with lot layout | Lot detail |

Each one is ~1-2 days of work: a print page component that fetches data and renders it, plus a config entry and a button.

---

## Implementation Order

**Phase 1: Generate Dialog + API Extensions (~2-3 days)**
1. Build `<GenerateDocumentDialog>` component using `Dialog` from shadcn/ui
2. Extend `POST /api/reports/download/` — accept `save_to_dms`, `classification`; create Documents record when requested
3. Extend `POST /api/reports/generate/` — accept `email_to[]`, `save_to_dms`, `classification`
4. Extend `useReportEmail.ts` — add options parameter to both `downloadReport()` and `requestReport()`
5. Test dialog with existing `spc` report type to verify all three paths (download, email, DMS save)

**Phase 2: Part Labels (~3-4 days)**
1. `npm install qrcode.react jsbarcode`
2. Build `<PartLabel>` component with QR + barcode + text layout
3. Build `<Barcode>` wrapper component for JsBarcode (thin SVG ref wrapper)
4. Build `PartLabelPrintPage` with Avery 5160 CSS grid
5. Add REPORT_CONFIG entries (`part_label_sheet`, `part_label_single`)
6. Add route in `router.tsx` (include `validateSearch` for `ids` and `woId` query params — see `spcPrintRoute` for pattern)
7. Extend `ReportType` union in `useReportEmail.ts` to include `"part_label_sheet" | "part_label_single"`
8. Add `id__in` filter to `PartFilter` in `Tracker/filters.py` (use `CharInFilter` pattern from existing `status__in` filter) — needed for single-label fetching by part ID
9. Add "Print Labels" button + dialog on WO detail page header
10. Add "Print Label" action in parts table row actions
11. Test with various batch sizes (1, 30, 100, 500)

**Phase 3: SPC Print Page — Wire to Real Data (~2-3 days)**
1. Import existing hooks: `useSpcHierarchy`, `useSpcData`, `useSpcCapability`, `useSpcActiveBaseline`
2. Delete mock data (processData array, generateMockData function)
3. Replace with hook calls, add type mapping functions if API shape differs from component types
4. Gate `data-print-ready` on all queries resolved
5. Add loading state
6. Update SPC page print button to use `<GenerateDocumentDialog>`
7. Test with real data: browser preview + `python manage.py generate_pdf spc`

**Phase 4: Polish (~1-2 days)**
1. Test generate dialog end-to-end with both verticals
2. Verify DMS save creates Documents with correct classification and source linkage
3. Verify email delivery for both types
4. Test batch label performance at 500 parts
5. Verify Playwright warm browser generates both types correctly via management command

**Total: ~8-12 days for both verticals + the reusable dialog.**

---

## Implementation Hints

| Feature | Existing Pattern | Where to Look |
|---------|-----------------|---------------|
| Dialog component | shadcn Dialog primitive | `ambac-tracker-ui/src/components/ui/dialog.tsx` |
| Report download | `downloadReport()` | `ambac-tracker-ui/src/hooks/useReportEmail.ts` |
| Report email | `requestReport()` | `ambac-tracker-ui/src/hooks/useReportEmail.ts` |
| DMS document creation | Documents record in Celery task | `Tracker/tasks.py` ~line 1540 |
| Classification enum | `ClassificationLevel` choices | `Tracker/models/core.py` — Documents model |
| SPC hierarchy hook | `useSpcHierarchy` | `ambac-tracker-ui/src/hooks/useSpcHierarchy.ts` |
| SPC data hook | `useSpcData` | `ambac-tracker-ui/src/hooks/useSpcData.ts` |
| SPC capability hook | `useSpcCapability` | `ambac-tracker-ui/src/hooks/useSpcCapability.ts` |
| SPC baseline hook | `useSpcActiveBaseline` | `ambac-tracker-ui/src/hooks/useSpcActiveBaseline.ts` |
| SPC interactive page (reference for real data usage) | Already wired to API | `ambac-tracker-ui/src/pages/SpcPage.tsx` |
| Traveler data endpoint | Part step-by-step history | `api_Parts_traveler_retrieve()` in generated client |
| Print page wrapper | `PrintLayout` with `data-print-ready` | `ambac-tracker-ui/src/components/print-layout.tsx` |
| REPORT_CONFIG | Config-driven PDF generation | `Tracker/services/pdf_generator.py` |
| WO detail action buttons | Status action buttons in header | `ambac-tracker-ui/src/pages/WorkOrderDetailPage.tsx` ~line 143 |
| Route definitions | Lazy-loaded print routes | `ambac-tracker-ui/src/router.tsx` ~line 524 (spcPrintRoute example) |
| Parts list API | Fetch parts by WO or IDs | `api_Parts_list()` in generated client |
