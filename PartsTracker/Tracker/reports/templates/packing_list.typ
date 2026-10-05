// Packing list — what is in one outbound shipment.
//
// Context: Tracker/reports/adapters/shipment_documents.py → ShipmentDocumentContext
//
// For the customer's receiving: every item and serial, the orders they fill, and the
// ERP's paperwork number. No prices: invoicing belongs to the ERP.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))
#let optd(v) = if v == none { text(fill: muted)[—] } else { str(v) }

#show: page-setup.with(
  title: "Packing List",
  doc-id: data.shipment_number,
  classification: "Packing List",
)

#report-title(
  [PACKING LIST],
  data.shipment_number,
  data.our_org,
  generated: data.issued_date,
)

#v(10pt)

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

#grid(
  columns: (1fr, 1fr), column-gutter: 20pt,
  [
    *Packed by (#data.our_org)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[#if data.shipped_by != none [#data.shipped_by · ] Date]
  ],
  [
    *Received by (customer)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date · Condition on arrival]
  ],
)
