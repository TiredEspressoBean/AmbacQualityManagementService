// Over-and-above scope for a lot — several of one customer's units, sent and answered
// together.
//
// Context: Tracker/reports/adapters/over_and_above_scope.py → OverAndAboveLotContext
//
// Scope only, as on the single-unit sheet: no prices. Each unit is answered on its own
// line — authorise or decline — and recorded on that core.

#import "_common/frame.typ": *
#import "_common/kitting.typ": tick
#import "_common/over_and_above.typ": scope-items

#let data = json.decode(sys.inputs.at("data"))
#let optd(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: doc-frame.with(
  doc-type: "Over-and-Above Scope",
  title: if data.customer_name != none { data.customer_name } else { data.reference },
  doc-id: data.reference,
  kind: "customer",
  subtitle: [#data.units.len() units · Additional work for your authorisation · Issued #data.issued_date],
  org: data.our_org,
)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Customer", text(weight: "semibold")[#opt(data.customer_name)]),
  field("From", data.our_org),
  field("Units", str(data.units.len())),
  field("Our reference", data.reference),
)

#divider()

#info-box[
  Teardown and inspection of these units found the conditions below. Each needs work
  beyond the rebuild level ordered, so it goes ahead only with your authorisation. Each
  unit lists the work, the parts it needs, and the finding behind it. Answer each unit
  on the last page.
]

#for u in data.units [
  #block(breakable: false)[
    = #if u.serial != none [#u.serial] else [#u.core_number] — #u.unit
    #grid(
      columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 4pt,
      field("Our reference", u.core_number),
      field("Order", opt(u.order)),
      field("Received", optd(u.received_date)),
      field("Rebuild level ordered", opt(u.entry_scope)),
    )
  ]
  #v(4pt)
  #scope-items(u.lines)
  #v(10pt)
]

#block(breakable: false)[
  = Your answer
  #text(size: 9.5pt)[
    Tick one box for each unit and return this sheet, quoting our reference
    #text(font: mono-font)[#data.reference].
  ]
  #v(6pt)
  #report-table(
    (1.4fr, 1.2fr, auto, auto),
    ("Unit", "Our reference", "Authorise", "Decline — return unrepaired"),
    data.units.map(u => (
      if u.serial != none { u.serial } else { u.core_number },
      text(font: mono-font, size: 8.5pt)[#u.core_number],
      align(center, tick()),
      align(center, tick()),
    )),
  )
  #v(18pt)
  #signature-block(
    (
      (role: [Customer], caption: "Name · Signature · Date"),
      (role: [Your reference], caption: "Reference"),
      (role: [Issued by (#data.our_org)], name: data.issued_by, caption: "Name · Signature · Date"),
    ),
    heading: none,
  )
]
