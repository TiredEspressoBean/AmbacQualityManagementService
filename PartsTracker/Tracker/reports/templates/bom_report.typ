// BOM Report template.
//
// Context: Tracker/reports/adapters/bom_report.py → BOMReportContext
//
// Layout:
//   1. Title block — report title, BOM status badge, tenant name
//   2. Header info grid — parent part, revision, type, effective date
//   3. Component table — Find # | Part Number | Description | Qty | UoM | Optional | Notes
//   4. Footer note (shop reference document, not a quality record)

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared kv / badge / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Status badge — the BOM's own vocabulary (DRAFT / RELEASED / OBSOLETE), which
// no other report shares. `optional-badge` is the kit's.
#let status-badge(status) = {
  if status == "RELEASED" { tone-badge("RELEASED", "ok") }
  else if status == "DRAFT" { tone-badge("DRAFT", "warn") }
  else if status == "OBSOLETE" { tone-badge("OBSOLETE", "bad") }
  else { tone-badge(status, "muted") }
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: page-setup.with(
  title: "Bill of Materials",
  classification: "Internal — Shop Reference",
)

// ── Title block ──────────────────────────────────────────────────────────────

#report-title(
  [BILL OF MATERIALS],
  data.parent_part_name,
  data.tenant_name,
  trailing: [
    #status-badge(data.status)
  ],
)

#v(14pt)

// ── Header info ──────────────────────────────────────────────────────────────

#info-box[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 6pt,

    kv("Part Number:", data.parent_part_number),
    kv("Revision:", data.revision),
    kv("Part Name:", data.parent_part_name),
    kv("BOM Type:", data.bom_type),
    kv("Status:", data.status),
    kv("Effective Date:", if data.effective_date != none { data.effective_date } else { "—" }),
  )
]

#v(14pt)

// ── Component table ──────────────────────────────────────────────────────────

= Components — #data.total_line_count lines

#if data.lines.len() == 0 [
  #text(fill: muted, style: "italic")[
    No component lines defined for this bill of materials.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  #report-table(
    (0.7fr, 1.5fr, 2.5fr, 0.6fr, 0.6fr, 0.65fr, 2fr),
    ([Find \#], [Part Number], [Description], [Qty], [UoM], [Opt?], [Notes]),
    data.lines.map(line => (
      text(fill: muted, font: mono-font)[#line.find_number],
      text(font: mono-font)[#line.component_part_number],
      text(font: sans-font)[#line.component_name],
      text(weight: "semibold")[#line.quantity],
      text(fill: muted)[#line.unit_of_measure],
      optional-badge(line.is_optional),
      text(fill: muted, size: 8.5pt)[#line.notes],
    )),
    column-gutter: 6pt,
    aligns: (left, left, left, right, left, center, left),
  )
]

#v(16pt)
#divider()

// ── Footer note ───────────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *Note:* This is a shop reference document. It is not a controlled quality
  record. The released engineering BOM is maintained in the PLM/ERP system.
  Total lines: #data.total_line_count.
  Status: #data.status. Revision: #data.revision.
]
