// Return-to-Vendor (RTV) sheet — travels with rejected material back to the supplier.
//
// Context: Tracker/reports/adapters/rtv_sheet.py → RtvSheetContext
//
// What is coming back and why, so the supplier can match it. No prices: credit for
// returned goods is settled in the ERP.

#import "_common/page-setup.typ": *
#import "_common/components.typ": *

#let data = json.decode(sys.inputs.at("data"))

#show: page-setup.with(
  title: "Return to Vendor",
  doc-id: data.lot_number,
  classification: "Return to Vendor",
)

#report-title(
  [RETURN TO VENDOR],
  data.lot_number,
  data.our_org,
  generated: data.issued_date,
)

#v(10pt)

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

#grid(
  columns: (1fr, 1fr), column-gutter: 20pt,
  [
    *Shipped by (#data.our_org)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date · Carrier / tracking]
  ],
  [
    *Received by (supplier)* \
    #v(28pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date · Your RMA number]
  ],
)
