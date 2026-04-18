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

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

#let badge(label, fg, bg) = box(
  fill: bg, inset: (x: 6pt, y: 2pt), radius: 3pt,
  text(size: 8.5pt, weight: "semibold", fill: fg, font: sans-font)[#label]
)

// Result badge — PASS=green, FAIL=red, LIMITED=amber
#let result-badge(result) = {
  if result == "PASS" { badge("PASS", ok, rgb("#dcfce7")) }
  else if result == "FAIL" { badge("FAIL", bad, rgb("#fee2e2")) }
  else if result == "LIMITED" { badge("LIMITED / RESTRICTED USE", warn, rgb("#fef3c7")) }
  else { badge(result, muted, rgb("#e2e8f0")) }
}

// Tolerance badge for the as-found status
#let tolerance-badge(in_tol) = {
  if in_tol == true { badge("IN TOLERANCE", ok, rgb("#dcfce7")) }
  else if in_tol == false { badge("OUT OF TOLERANCE", bad, rgb("#fee2e2")) }
  else { badge("NOT RECORDED", muted, rgb("#e2e8f0")) }
}

// Calibration type — turn AFTER_REPAIR → "After Repair"
#let fmt-cal-type(t) = t.replace("_", " ").split(" ").map(w =>
  upper(w.first()) + lower(w.slice(1))
).join(" ")

// Field/value row — muted label, value in ink; handles none/empty gracefully
#let kv(label, value) = grid(
  columns: (auto, 1fr),
  column-gutter: 10pt,
  text(fill: muted, font: sans-font, size: 9pt)[*#label*],
  if value == none or value == "" [
    #text(fill: muted, style: "italic")[—]
  ] else [
    #value
  ],
)

// Section divider rule
#let divider() = {
  v(6pt)
  line(length: 100%, stroke: 0.4pt + rule)
  v(6pt)
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Calibration Certificate",
  doc-id: data.certificate_number,
  classification: "Controlled Document — ISO 17025",
)

// ── Title block ──────────────────────────────────────────────────────────────

#align(center)[
  #text(size: 9pt, fill: muted, tracking: 2pt, font: sans-font)[
    CALIBRATION CERTIFICATE
  ]
  #v(2pt)
  #text(size: 22pt, weight: "bold", font: sans-font)[#data.certificate_number]
  #v(-4pt)
  #text(size: 10pt, fill: muted)[#data.tenant_name]
  #v(6pt)
  #result-badge(data.result)
]

#v(12pt)

// ── Equipment under test ──────────────────────────────────────────────────────

= Equipment Under Test

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  kv("Instrument Name", data.equipment_name),
  kv("Serial Number", data.equipment_serial),

  kv("Equipment Type", data.equipment_type),
  kv("Manufacturer", data.equipment_manufacturer),

  kv("Model Number", data.equipment_model),
  kv("Location", data.equipment_location),
)

#divider()

// ── Calibration details ──────────────────────────────────────────────────────

= Calibration Details

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  row-gutter: 6pt,

  kv("Calibration Date", str(data.calibration_date)),
  kv("Next Due Date", str(data.due_date)),

  kv(
    "Calibration Type",
    fmt-cal-type(data.calibration_type),
  ),
  kv("Performed By", data.performed_by),

  kv("External Lab", data.external_lab),
  kv("", none),
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
      #badge("YES — ADJUSTED", warn, rgb("#fef3c7"))
    ] else [
      #badge("NO ADJUSTMENT", ok, rgb("#dcfce7"))
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
