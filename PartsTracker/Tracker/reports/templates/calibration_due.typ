// Calibration Due Report template.
//
// Context: Tracker/reports/adapters/calibration_due.py → CalibrationDueContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Summary bar — total / overdue / due-soon counts
//   3. Equipment table — sorted by due_date ascending (overdue first)
//   4. Footer note (planning document, not a quality record)

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

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

#show: page-setup.with(
  title: "Calibration Due Report",
  classification: "Internal — Quality Planning",
)

// ── Title block ──────────────────────────────────────────────────────────────

#report-title(
  [CALIBRATION DUE REPORT],
  [Calibration Status],
  data.tenant_name,
  generated: data.generated_date,
)

#v(14pt)

// ── Summary bar ──────────────────────────────────────────────────────────────

#info-box[
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 12pt,

    // Total
    align(center)[
      #text(size: 22pt, weight: "bold", font: sans-font)[#data.total_equipment]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Total Equipment Tracked]
    ],

    // Overdue
    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.overdue_count > 0 { bad } else { ok },
      )[#data.overdue_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Overdue]
    ],

    // Due Soon
    align(center)[
      #text(
        size: 22pt, weight: "bold", font: sans-font,
        fill: if data.due_soon_count > 0 { warn } else { ok },
      )[#data.due_soon_count]
      #v(-4pt)
      #text(size: 9pt, fill: muted, font: sans-font)[Due Within 30 Days]
    ],
  )
]

#v(14pt)

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
    (2.5fr, 1.8fr, 1.4fr, 1.1fr, 1.1fr, 0.7fr, 1fr),
    ([Equipment], [Serial], [Location], [Last Cal], [Due Date], [Days], [Status]),
    data.items.map(item => (
      text(font: sans-font)[#item.equipment_name],
      text(fill: muted, font: mono-font)[#item.equipment_serial],
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
