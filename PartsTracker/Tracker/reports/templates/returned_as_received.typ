// Returned as received — a customer's own unit going back without the repair.
//
// Context: Tracker/reports/adapters/returned_as_received.py → ReturnedAsReceivedContext
//
// Not a Certificate of Conformance: nothing was made or repaired to certify. It says the
// unit went back unrepaired at the customer's request, what was found, and their answer.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let optd(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: doc-frame.with(
  doc-type: "Returned As Received",
  title: data.shipment_number,
  doc-id: data.shipment_number,
  kind: "customer",
  subtitle: [Issued #data.issued_date],
  org: data.our_org,
)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Customer", text(weight: "semibold")[#data.customer_name]),
  field("From", data.our_org),
  field("Shipment", data.shipment_number),
  field("Shipped", optd(data.shipped_date)),
)

#divider()

#info-box[
  The unit(s) below are returned without repair, at the customer's request. The repair
  scope proposed after inspection was declined; the unit(s) are returned in the
  condition received, and no conformance to a repair standard is certified.
]

#for u in data.units [
  #v(8pt)
  #block(breakable: false)[
    = #if u.serial != none [#u.serial] else [#u.core_number]
    #grid(
      columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
      field("Unit", u.part_type),
      field("Our reference", u.core_number),
      field("Order", opt(u.order)),
      field("Declined on", optd(u.answered_on)),
      field("Answered by", opt(u.answered_by)),
      field("How", opt(u.method)),
      field("Customer reference", opt(u.reference)),
    )
    #v(4pt)
    #text(weight: "semibold")[Findings behind the declined scope]
    #if u.findings.len() == 0 [
      #text(fill: muted)[None recorded.]
    ] else [
      #list(..u.findings.map(f => [#f]))
    ]
  ]
]

#v(22pt)

#signature-block(
  ((role: [Issued by (#data.our_org)], name: data.issued_by, caption: "Name · Signature · Date"), none),
  heading: none,
)
