// Certificate of Conformance — for everything on one outbound shipment.
//
// Context: Tracker/reports/adapters/shipment_documents.py → ShipmentDocumentContext
//
// States that the listed items were made and inspected to the order's requirements,
// with the serials so the customer can match each unit. Signed by whoever issues it.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: page-setup.with(
  title: "Certificate of Conformance",
  doc-id: data.shipment_number,
  classification: "Certificate of Conformance",
)

#report-title(
  [CERTIFICATE OF CONFORMANCE],
  data.shipment_number,
  data.our_org,
  generated: data.issued_date,
)

#v(10pt)

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Customer", text(weight: "semibold")[#data.customer_name]),
  field("Supplier", data.our_org),
  field("Order(s)", if data.orders.len() == 0 { text(fill: muted)[—] } else { data.orders.join(", ") }),
  field("Shipment", data.shipment_number),
  field("Shipped", str(data.shipped_date)),
  field("Reference", opt(data.reference)),
)

#divider()

= Items certified

#report-table(
  (auto, 1fr, auto),
  ("Order · line", "Item · serials", "Qty"),
  data.items.map(i => (
    [#opt(i.order)#if i.line != none [ · #i.line]],
    [#text(weight: "semibold")[#i.part_type] \ #text(size: 8.5pt, fill: muted)[#i.serials.join(", ")]],
    str(i.quantity),
  )),
  aligns: (left, left, right),
)

#v(10pt)

#info-box[
  We certify that the items listed above were manufactured, inspected and tested in
  accordance with the requirements of the order(s) referenced, and conform to those
  requirements. Records supporting this certification are retained by #data.our_org
  and are available on request.
]

#v(22pt)

#grid(
  columns: (1fr, 1fr), column-gutter: 20pt,
  [
    *Authorized by (#data.our_org)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[#if data.issued_by != none [#data.issued_by · ] Quality · Date]
  ],
  [],
)
