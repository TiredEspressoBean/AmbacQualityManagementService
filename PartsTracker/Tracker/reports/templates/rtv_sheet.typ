// Return-to-Vendor (RTV) sheet — travels with rejected material back to the supplier.
//
// Context: Tracker/reports/adapters/rtv_sheet.py → RtvSheetContext
//
// What is coming back and why, so the supplier can match it. No prices: credit for
// returned goods is settled in the ERP.

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: doc-frame.with(
  doc-type: "Return to Vendor",
  title: data.lot_number,
  doc-id: data.lot_number,
  kind: "supplier",
  subtitle: [Issued #data.issued_date],
  org: data.our_org,
)

= Returning to

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Supplier", text(weight: "semibold")[#opt(data.supplier_name)]),
  field("From", data.our_org),
  field("Issued by", opt(data.issued_by)),
  field("Date", str(data.issued_date)),
)

#divider()

= Material

#grid(
  columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 6pt,
  field("Item", [#text(weight: "semibold")[#data.item_name] #if data.part_number != none [ · #data.part_number ]]),
  field("Quantity returned", text(weight: "semibold")[#data.quantity]),
  field("Our lot", data.lot_number),
  field("Your lot", opt(data.supplier_lot_number)),
  field("Heat number", opt(data.heat_number)),
  field("PO / line", opt(data.erp_po)),
  field("Received", if data.received_date == none { text(fill: muted)[—] } else { str(data.received_date) }),
  field("Disposition", opt(data.disposition_number)),
  field("Your RMA", opt(data.at("rma_number", default: none))),
)

#divider()

= Reason for return

#if data.reason == "" [
  #text(fill: muted, style: "italic")[See the disposition referenced above.]
] else [ #data.reason ]

#if data.scar_numbers.len() > 0 [
  #v(8pt)
  #block(
    width: 100%, fill: warn-tint, stroke: 0.5pt + warn,
    inset: (x: 10pt, y: 8pt), radius: 4pt,
  )[
    #text(weight: "semibold", fill: warn, font: sans-font)[Corrective action requested] —
    SCAR #data.scar_numbers.join(", ") has been sent separately; please respond to it.
  ]
]

#v(18pt)

#signature-block((
  (role: [Shipped by (#data.our_org)], caption: "Name · Date · Carrier / tracking"),
  (role: "Received by (supplier)", caption: "Name · Date"),
), heading: none)
