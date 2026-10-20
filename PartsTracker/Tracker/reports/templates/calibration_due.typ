// Calibration Due Report template.
//
// Context: Tracker/reports/adapters/calibration_due.py → CalibrationDueContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Summary bar — total / overdue / due-soon counts
//   3. Equipment table — sorted by due_date ascending (overdue first)
//   4. Footer note (planning document, not a quality record)

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared badge / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Status badge — OVERDUE=red, DUE_SOON=amber, CURRENT=green
#let status-badge(status) = {
  if status == "OVERDUE"  { tone-badge("OVERDUE", "bad") }
  else if status == "DUE_SOON" { tone-badge("DUE SOON", "warn") }
  else                    { tone-badge("CURRENT", "ok") }
}

// Result badge — PASS=green, FAIL=red, LIMITED=amber
#let result-badge(result) = {
  if result == "PASS"    { tone-badge("PASS", "ok") }
  else if result == "FAIL" { tone-badge("FAIL", "bad") }
  else if result == "LIMITED" { tone-badge("LIMITED", "warn") }
  else                   { tone-badge(result, "muted") }
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: doc-frame.with(
  doc-type: "Calibration Due Report",
  title: [Calibration Status],
  kind: "shop",
  org: data.tenant_name,
)

#stat-panel((
  (value: data.total_equipment, label: "Total Equipment Tracked"),
  (value: data.overdue_count, label: "Overdue", tone: if data.overdue_count > 0 { "bad" } else { "ok" }),
  (value: data.due_soon_count, label: "Due Within 30 Days", tone: if data.due_soon_count > 0 { "warn" } else { "ok" }),
))

// ── Equipment table ──────────────────────────────────────────────────────────

= Equipment Calibration Status

#if data.items.len() == 0 [
  #text(fill: muted, style: "italic")[
    No equipment with calibration records found for this tenant.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  #report-table(
    // IDs and badges size to their content — a serial split at its hyphens reads as two.
    (2.3fr, auto, 1.4fr, 1.1fr, 1.1fr, 0.6fr, auto),
    ([Equipment], [Serial], [Location], [Last Cal], [Due Date], [Days], [Status]),
    data.items.map(item => (
      text(font: sans-font)[#item.equipment_name],
      box(text(fill: muted, font: mono-font)[#item.equipment_serial]),
      text(fill: muted)[#item.location],
      text(fill: muted)[#item.last_cal_date],
      text(
        fill: if item.status == "OVERDUE" { bad }
              else if item.status == "DUE_SOON" { warn }
              else { ink },
        weight: if item.status == "OVERDUE" { "semibold" } else { "regular" },
      )[#item.due_date],
      {
        let days = item.days_until_due
        text(
          fill: if days < 0 { bad } else if days <= 30 { warn } else { muted },
          weight: if days < 0 { "semibold" } else { "regular" },
        )[#if days < 0 [#str(days)] else [+#str(days)]]
      },
      status-badge(item.status),
    )),
    column-gutter: 6pt,
    aligns: (left, left, left, left, left, right, center),
  )
]

#v(16pt)

// ── Footer note ───────────────────────────────────────────────────────────────

#footer-note([
  This is a planning document generated from calibration record data as
  of #data.generated_date. It is not a calibration certificate or quality record.
  Status thresholds: OVERDUE = past due date; DUE SOON = due within 30 days;
  CURRENT = more than 30 days remaining.
])
