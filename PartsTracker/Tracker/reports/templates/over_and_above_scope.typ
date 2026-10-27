// Over-and-above scope — additional work on a customer's unit, sent for their authorisation.
//
// Context: Tracker/reports/adapters/over_and_above_scope.py → OverAndAboveScopeContext
//
// Scope only: what work, what parts, and the finding behind each. No prices — pricing
// happens in the system that owns it. The customer's answer comes back on this sheet
// (or by any other route) and is recorded on the core.

#import "_common/frame.typ": *
#import "_common/kitting.typ": tick
#import "_common/over_and_above.typ": scope-items

#let data = json.decode(sys.inputs.at("data"))
#let optd(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: doc-frame.with(
  doc-type: "Over-and-Above Scope",
  title: if data.serial != none { data.serial } else { data.core_number },
  doc-id: data.core_number,
  kind: "customer",
  subtitle: [Additional work for your authorisation · Issued #data.issued_date],
  org: data.our_org,
)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Customer", text(weight: "semibold")[#opt(data.customer_name)]),
  field("From", data.our_org),
  field("Unit", data.unit),
  field("Serial", opt(data.serial)),
  field("Our reference", data.core_number),
  field("Order", opt(data.order)),
  field("Received", optd(data.received_date)),
  field("Rebuild level ordered", opt(data.entry_scope)),
)

#divider()

#info-box[
  Teardown and inspection of this unit found the conditions below. Each needs work
  beyond the rebuild level ordered, so it goes ahead only with your authorisation.
  Each item lists the work, the parts it needs, and the finding behind it.
]

#scope-items(data.lines)

#v(14pt)

#block(breakable: false)[
  = Your answer
  #text(size: 9.5pt)[
    Tick one and return this sheet, quoting our reference #text(font: mono-font)[#data.core_number].
  ]
  #v(6pt)
  #grid(
    columns: (auto, 1fr), column-gutter: 8pt, row-gutter: 8pt, align: horizon,
    tick(), [Authorise the work above],
    tick(), [Decline — return the unit unrepaired],
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
