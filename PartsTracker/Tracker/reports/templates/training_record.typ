// Training Record template.
//
// Context: Tracker/reports/adapters/training_record.py → TrainingRecordContext
//
// Layout:
//   1. Title block — report title, generated date, tenant name
//   2. Employee info header — name, email/ID
//   3. Summary bar — total / current / expired / no-expiry counts
//   4. Training table — topic, completed, expires, trainer, status badge
//   5. ISO 9001 7.2 note (competence evidence, not just attendance)
//   6. Signature block — Employee, Trainer, Supervisor (3-column)

#import "_common/frame.typ": *

#let data = json.decode(sys.inputs.at("data"))

// ----------------------------------------------------------------------------
// Helpers — shared kv / badge / divider come from _common/components.typ
// ----------------------------------------------------------------------------

// Status badge — CURRENT=green, EXPIRED=red, EXPIRING_SOON=amber, no expiry=muted
#let status-badge(status) = {
  if status == "CURRENT"        { tone-badge("CURRENT", "ok") }
  else if status == "EXPIRED"   { tone-badge("EXPIRED", "bad") }
  else if status == "EXPIRING_SOON" { tone-badge("EXPIRING SOON", "warn") }
  else                          { tone-badge(status, "muted") }
}

// ----------------------------------------------------------------------------
// Document
// ----------------------------------------------------------------------------

#show: doc-frame.with(
  doc-type: "Training Record",
  title: data.employee_name,
  kind: "record",
  org: data.tenant_name,
)

// ── Employee info ─────────────────────────────────────────────────────────────

#info-box[
  #text(size: 9pt, weight: "semibold", fill: muted, font: sans-font)[EMPLOYEE]
  #v(6pt)
  #kv("Name:", data.employee_name)
  #v(2pt)
  #kv("Email / ID:", data.employee_email)
  #v(2pt)
]

#v(14pt)

// ── Summary ──────────────────────────────────────────────────────────────────

#stat-panel((
  (value: data.total_count, label: "Total"),
  (value: data.current_count, label: "Current", tone: if data.current_count > 0 { "ok" } else { "plain" }),
  (value: data.expired_count, label: "Expired", tone: if data.expired_count > 0 { "bad" } else { "plain" }),
  (value: data.no_expiry_count, label: "No Expiry"),
))

#v(14pt)

// ── Training table ────────────────────────────────────────────────────────────

= Training History

#if data.records.len() == 0 [
  #text(fill: muted, style: "italic")[
    No training records found for this employee.
  ]
] else [
  #set text(size: 9pt)
  #set par(justify: false)

  #report-table(
    (2.6fr, 1.1fr, 0.9fr, 1.1fr, 1.5fr, 1.0fr),
    ([Training Topic], [Completed], [Level], [Expires], [Trainer / Provider],
     [Status]),
    data.records.map(rec => (
      {
        text(font: sans-font, weight: "semibold")[#rec.topic]
        if rec.notes != "" [
          #v(1pt)
          #text(size: 8pt, fill: muted)[#rec.notes]
        ]
      },
      text(fill: muted)[#rec.completed_date],
      text(font: sans-font, weight: "semibold")[L#rec.level],
      if rec.expires_date != none {
        text(
          fill: if rec.status == "EXPIRED" { bad }
                else if rec.status == "EXPIRING_SOON" { warn }
                else { muted },
        )[#rec.expires_date]
      } else {
        text(fill: muted, style: "italic")[—]
      },
      if rec.trainer != "" {
        text(fill: muted)[#rec.trainer]
      } else {
        text(fill: muted, style: "italic")[—]
      },
      status-badge(rec.status),
    )),
    column-gutter: 6pt,
    aligns: (left, left, center, left, left, center),
  )
]

#v(16pt)
#divider()

// ── ISO 9001 §7.2 note ────────────────────────────────────────────────────────

#text(size: 8.5pt, fill: muted)[
  *ISO 9001:2015 §7.2 — Competence:* This record demonstrates the effectiveness
  of training as required by the standard. Assessment results and competency
  evaluations must be retained as documented information. Status: CURRENT =
  valid and within expiry date; EXPIRING SOON = expires within 30 days;
  EXPIRED = past expiry date; NO EXPIRY = no expiry date defined (evergreen).
]

#v(20pt)

#signature-block(
  (
    (role: "Employee", hint: "Acknowledging attendance", name: data.employee_name),
    (role: "Trainer", hint: "Confirming delivery"),
    (role: "Supervisor", hint: "Confirming competency"),
  ),
  intro: text(size: 9pt, fill: muted)[
    Signatures below confirm attendance (Employee), training delivery (Trainer),
    and verification of competency (Supervisor/Manager).
  ],
)
