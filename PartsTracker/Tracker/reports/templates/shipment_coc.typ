// Certificate of Conformance — for everything on one outbound shipment.
//
// Context: Tracker/reports/adapters/shipment_documents.py → ShipmentDocumentContext
//
// States that the listed items were made and inspected to the order's requirements,
// with the serials so the customer can match each unit. Signed by whoever issues it.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Certificate of Conformance",
  title: data.shipment_number,
  doc-id: data.shipment_number,
  kind: "customer",
  subtitle: [Issued #data.issued_date],
  org: data.our_org,
)

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
    i.quantity,
  )),
  aligns: (left, left, right),
)

#v(10pt)

#info-box[
  We certify that the items listed above were #data.work_done, inspected and tested in
  accordance with the requirements of the order(s) referenced, and conform to those
  requirements. Records supporting this certification are retained by #data.our_org
  and are available on request.
]

#v(22pt)

#signature-block(
  // Signed by quality, never by whoever happened to issue it: blank for a QA signature
  // unless the issuer holds that authority.
  ((role: [Authorized by (#data.our_org)], name: data.authorized_by, caption: "Quality · Signature · Date"), none),
  heading: none,
)
