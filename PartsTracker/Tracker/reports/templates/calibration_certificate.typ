// Calibration Certificate template.
//
// Context: Tracker/reports/adapters/calibration_certificate.py → CalibrationCertificateContext
//
// Layout:
//   1. Title block — certificate number prominent, result badge
//   2. Equipment under test section
//   3. Calibration details section
//   4. As-found / as-left section
//   5. Standards used (NIST traceability)
//   6. Notes
//   7. Signature block — Calibration Technician + Reviewing Authority
//   8. "End of Certificate" marker (ISO 17025 requirement)

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared badge / field / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Result badge — PASS=green, FAIL=red, LIMITED=amber
#let result-badge(result) = {
  if result == "PASS" { tone-badge("PASS", "ok") }
  else if result == "FAIL" { tone-badge("FAIL", "bad") }
  else if result == "LIMITED" { tone-badge("LIMITED / RESTRICTED USE", "warn") }
  else { tone-badge(result, "muted") }
}

// Tolerance badge for the as-found status
#let tolerance-badge(in_tol) = {
  if in_tol == true { tone-badge("IN TOLERANCE", "ok") }
  else if in_tol == false { tone-badge("OUT OF TOLERANCE", "bad") }
  else { tone-badge("NOT RECORDED", "muted") }
}

// Calibration type — turn AFTER_REPAIR → "After Repair"
#let fmt-cal-type(t) = t.replace("_", " ").split(" ").map(w =>
  upper(w.first()) + lower(w.slice(1))
).join(" ")

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Calibration Certificate",
  doc-id: data.certificate_number,
  classification: "Controlled Document — ISO 17025",
)

// ── Title block ──────────────────────────────────────────────────────────────

#report-title(
  [CALIBRATION CERTIFICATE],
  data.certificate_number,
  data.tenant_name,
  title-size: 22pt,
  trailing: [
    #result-badge(data.result)
  ],
)

#v(12pt)

// ── Equipment under test ──────────────────────────────────────────────────────

= Equipment Under Test

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  field("Instrument Name", data.equipment_name),
  field("Serial Number", data.equipment_serial),

  field("Equipment Type", data.equipment_type),
  field("Manufacturer", data.equipment_manufacturer),

  field("Model Number", data.equipment_model),
  field("Location", data.equipment_location),
)

#divider()

// ── Calibration details ──────────────────────────────────────────────────────

= Calibration Details

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  field("Calibration Date", str(data.calibration_date)),
  field("Next Due Date", str(data.due_date)),

  field(
    "Calibration Type",
    fmt-cal-type(data.calibration_type),
  ),
  field("Performed By", data.performed_by),

  field("External Lab", data.external_lab),
  field("", none),
)

#divider()

// ── As-found / as-left ──────────────────────────────────────────────────────

= As-Found / As-Left Condition

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  [
    #text(fill: muted, font: sans-font, size: 9pt)[*As Found — In Tolerance*] \
    #v(2pt)
    #tolerance-badge(data.as_found_in_tolerance)
  ],
  [
    #text(fill: muted, font: sans-font, size: 9pt)[*Adjustments Made*] \
    #v(2pt)
    #if data.adjustments_made [
      #tone-badge("YES — ADJUSTED", "warn")
    ] else [
      #tone-badge("NO ADJUSTMENT", "ok")
    ]
  ],
)

#divider()

// ── Standards used ──────────────────────────────────────────────────────────

= Standards Used / Traceability

#if data.standards_used == "" [
  #text(fill: muted, style: "italic")[No standards recorded.]
] else [
  #data.standards_used

  #v(4pt)
  #text(size: 9pt, fill: muted)[
    All reference standards are traceable to NIST (National Institute of Standards
    and Technology) or equivalent national metrology institutes through an unbroken
    chain of comparisons.
  ]
]

// ── Notes ───────────────────────────────────────────────────────────────────

#if data.notes != "" [
  #divider()
  = Notes / Remarks

  #data.notes
]

#v(20pt)

// ── Signature block ──────────────────────────────────────────────────────────

= Signatures

#grid(
  columns: (1fr, 1fr),
  column-gutter: 24pt,

  [
    *Calibration Technician* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
  [
    *Reviewing Authority* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Signature · Date]
  ],
)

#v(24pt)

// ── End of Certificate marker (ISO 17025 requirement) ────────────────────────

#align(center)[
  #line(length: 60%, stroke: 0.5pt + rule)
  #v(4pt)
  #text(size: 9pt, fill: muted, font: sans-font, tracking: 1pt)[
    END OF CERTIFICATE — #data.certificate_number
  ]
  #v(2pt)
  #text(size: 8pt, fill: muted)[
    This certificate may not be reproduced except in full without written approval
    of the issuing laboratory.
  ]
]
