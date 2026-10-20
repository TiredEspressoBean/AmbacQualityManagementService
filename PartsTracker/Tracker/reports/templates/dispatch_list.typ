// Dispatch List template.
//
// Context: Tracker/reports/adapters/dispatch_list.py → DispatchListContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Summary bar — total open WOs, overdue count
//   3. Per work-center section:
//        Section heading: step name + WO count
//        Table: WO # | Part | Qty | Due Date | Days | Priority | Status
//        Overdue rows shown in red/bold
//   4. Footer note (planning document, not a quality record)

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared badge / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Priority badge comes from the kit (`wo-priority-badge`) — shared with the
// traveler so one work order can't print two different colours on two sheets.

// Status text colouring (WorkOrderStatus values)
#let status-color(s) = {
  if s == "IN_PROGRESS"         { ok   }
  else if s == "ON_HOLD"        { warn }
  else                          { muted }
}

// Human-friendly status label
#let status-label(s) = {
  let words = s.split("_").map(w => if w == "QA" { w } else { upper(w.first()) + lower(w.slice(1)) })
  words.join(" ")
}

// Days cell — red/bold when negative (overdue), amber when <= 3, otherwise muted
#let days-cell(d) = {
  if d == none [
    #text(fill: muted)[—]
  ] else {
    let dval = int(d)
    let col = if dval < 0 { bad } else if dval <= 3 { warn } else { muted }
    let wt  = if dval < 0 { "semibold" } else { "regular" }
    if dval < 0 {
      text(fill: col, weight: wt)[#str(dval)]
    } else {
      text(fill: col, weight: wt)[+#str(dval)]
    }
  }
}

// Column widths shared between header and data rows
#let col-widths = (1.3fr, 2fr, 0.5fr, 1fr, 0.55fr, 0.9fr, 1.4fr)

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: doc-frame.with(
  doc-type: "Dispatch List",
  title: [What's Running Today],
  kind: "shop",
  org: data.tenant_name,
)


// ── Summary ───────────────────────────────────────────────────────────────────

#stat-panel((
  (value: data.total_open_wos, label: "Total Open Work Orders"),
  (value: data.overdue_count, label: "Overdue", tone: if data.overdue_count > 0 { "bad" } else { "ok" }),
))

// ── Work center groups ────────────────────────────────────────────────────────

#if data.groups.len() == 0 [
  #empty-state[No open work orders.]
] else [
  #set par(justify: false)
  #set text(size: 9pt)
  #for group in data.groups [
    #group-band(group.step_name, count: [#group.wo_count WO#if group.wo_count != 1 [s]])
    #report-table(
      col-widths,
      ([WO \#], "Part", "Qty", "Due Date", "Days", "Priority", "Status"),
      group.items.map(item => {
        let late = item.days_until_due != none and int(item.days_until_due) < 0
        let flag(body) = text(fill: if late { bad } else { muted }, weight: if late { "semibold" } else { "regular" })[#body]
        (
          text(font: mono-font, fill: if late { bad } else { ink }, weight: if late { "semibold" } else { "regular" })[#item.wo_number],
          item.part_name,
          text(fill: muted)[#item.qty_remaining],
          flag(if item.due_date == none [—] else [#item.due_date]),
          days-cell(item.days_until_due),
          wo-priority-badge(item.priority),
          text(fill: status-color(item.status))[#status-label(item.status)],
        )
      }),
      aligns: (left, left, right, left, right, center, left),
    )
  ]
]

// ── Footer note ───────────────────────────────────────────────────────────────

#footer-note([
  Generated from live production data as of #data.generated_date — not a quality
  record or traveler. Work
  centers are approximated by the current manufacturing step assigned to each part.
  Sort order: most urgent (earliest due date) first within each work center.
  Days column: negative values indicate the work order is past its due date.
])
