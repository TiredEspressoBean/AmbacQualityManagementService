// Operator Hours template.
// Context: Tracker/reports/adapters/labor_hours.py → LaborHoursContext

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#let col-widths = (3fr, 1.2fr, 1.2fr, 1.2fr, 1.2fr)

#show: doc-frame.with(
  doc-type: "Operator Hours",
  title: [Shop Hours by Operator],
  kind: "shop",
  subtitle: [Period: #data.start_date — #data.end_date],
  org: data.tenant_name,
)

#stat-panel((
  (value: data.total_on_shift, label: "Total On-Shift Hours"),
  (value: data.total_direct, label: "Total Direct (Job) Hours"),
  (value: data.total_rework, label: "of which Rework"),
))

#if data.rows.len() == 0 [
  #empty-state[No hours logged in this period.]
] else [
  #set text(size: 9pt)
  #report-table(
    col-widths,
    ("Operator", "On-Shift hrs", "Direct hrs", "Rework hrs", "Unallocated hrs"),
    data.rows.map(r => (
      r.name,
      text(font: mono-font)[#r.on_shift_hours],
      text(font: mono-font)[#r.direct_hours],
      text(font: mono-font, fill: muted)[#r.rework_hours],
      text(font: mono-font, fill: muted)[#r.unallocated_hours],
    )) + ((
      text(weight: "semibold")[Total],
      text(font: mono-font, weight: "semibold")[#data.total_on_shift],
      text(font: mono-font, weight: "semibold")[#data.total_direct],
      text(font: mono-font, weight: "semibold")[#data.total_rework],
      text(font: mono-font, weight: "semibold")[#data.total_unallocated],
    ),),
    aligns: (left, right, right, right, right),
  )
]

#footer-note(
  lead: "Note",
  [On-shift = clock-in→out attendance, breaks excluded. Direct = time on the operator's step records, within on-shift time, concurrent jobs shared, holds and outside processing excluded; rework (a re-visit or rework step) is part of direct. Unallocated = on-shift − direct. Shop-floor operators only. Hours data for payroll — not a payroll calculation.],
)
