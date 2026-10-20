// Packing list — what is in one outbound shipment.
//
// Context: Tracker/reports/adapters/shipment_documents.py → ShipmentDocumentContext
//
// For the customer's receiving: every item and serial, the orders they fill, and the
// ERP's paperwork number. No prices: invoicing belongs to the ERP.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let optd(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: doc-frame.with(
  doc-type: "Packing List",
  title: data.shipment_number,
  doc-id: data.shipment_number,
  kind: "customer",
  subtitle: [Issued #data.issued_date],
  org: data.our_org,
)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Ship to", [#text(weight: "semibold")[#data.customer_name] #if data.customer_address != none [ \ #data.customer_address ]]),
  field("From", data.our_org),
  field("Shipped", str(data.shipped_date)),
  field("Expected delivery", optd(data.expected_delivery)),
  field("Carrier", opt(data.carrier)),
  field("Tracking", opt(data.tracking_number)),
  field("Order(s)", if data.orders.len() == 0 { text(fill: muted)[—] } else { data.orders.join(", ") }),
  field("Reference", opt(data.reference)),
)

#divider()

= Contents

#report-table(
  (auto, auto, 1fr, auto),
  ("Order", "Line", "Item · serials", "Qty"),
  data.items.map(i => (
    opt(i.order),
    if i.line == none { text(fill: muted)[—] } else { str(i.line) },
    [#text(weight: "semibold")[#i.part_type] \ #text(size: 8.5pt, fill: muted)[#i.serials.join(", ")]],
    i.quantity,
  )),
  aligns: (left, right, left, right),
)

#align(right)[#text(weight: "semibold")[Serialised units: #data.total_units]]

#v(18pt)

#signature-block((
  (role: [Packed by (#data.our_org)], name: data.shipped_by, caption: "Name · Date"),
  (role: "Received by (customer)", caption: "Name · Date · Condition on arrival"),
), heading: none)
