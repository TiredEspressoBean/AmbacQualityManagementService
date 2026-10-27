// Over-and-above scope items: one block per repair awaiting the customer — the work,
// the finding behind it, and the parts it needs. Shared by the single-unit sheet and
// the lot sheet so both print an item the same way.

#import "frame.typ": *

#let part-line(p) = [
  #text(weight: "semibold")[#p.component]
  #if p.part_number != none [ #box(text(font: mono-font, size: 8.5pt)[#p.part_number])]
  #if p.position != none [ · #p.position]
  · #text(fill: muted)[#p.source]
]

#let scope-items(lines) = for (i, l) in lines.enumerate() [
  #block(breakable: false)[
    #group-band(
      [#l.code#if l.name != none [ — #l.name]],
      count: [Item #(i + 1) of #lines.len()],
    )
    #report-table(
      (1fr, 1.6fr, 1.4fr),
      ("Work", "Finding behind it", "Parts needed"),
      ((
        if l.work.len() == 0 { text(fill: muted)[As named above] }
        else { stack(spacing: 4pt, ..l.work.map(w => [#w])) },
        if l.findings.len() == 0 { text(fill: muted)[None recorded] }
        else { stack(spacing: 4pt, ..l.findings.map(f => [#f])) },
        if l.parts.len() == 0 { text(fill: muted)[No replacement parts] }
        else { stack(spacing: 4pt, ..l.parts.map(part-line)) },
      ),),
      valign: top,
    )
  ]
]
