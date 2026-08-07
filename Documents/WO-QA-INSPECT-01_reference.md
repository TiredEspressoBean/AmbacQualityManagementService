# Work order reference — WO-QA-INSPECT-01

Companion to `UQMES_ONBOARDING_WALKTHROUGH.md`. This is the single demo work
order the walkthrough runs against — its identity, routing, and the exact
pre-staged state of each part. The demo tenant is reset to this state before
each run (`python manage.py seed_demo`), so every exhibit the walk references is
always present.

There is also a scannable traveler PDF at
`artifacts/WO-QA-INSPECT-01_traveler.pdf` — the paper counterpart to the routing
table below, with the header barcode/QR and per-operation sign-off blocks.

---

## Header

| Field | Value |
|---|---|
| Work order | **WO-QA-INSPECT-01** |
| Status | IN_PROGRESS |
| Quantity | 8 parts |
| Due | ~8 days out (seeded relative to the reseed date — don't key on a fixed date) |
| Order | **QA Inspector Onboarding Walkthrough** (`ORD-2024-QA-INSPECT`) |
| Customer / company | Midwest Fleet Services |
| Part type | Common Rail Injector |
| Process | **Injector Reman** (12 operations) |

---

## Routing — the 12 operations

Injector reman, in operation order. The QA gates are what the walkthrough
exercises; the flags map straight onto the step-authoring switches in §14d/§14g.

| Op | Step | QA gates |
|---:|---|---|
| 10 | Core Receiving | QA sign-off · decision |
| 20 | Disassembly | — |
| 30 | Component Grading | QA sign-off · decision |
| 40 | Cleaning | — |
| 50 | **Nozzle Inspection** | **FPI** · QA sign-off · **sampling** · decision |
| 60 | **Flow Testing** | **FPI** · QA sign-off · **sampling** · decision |
| 70 | Assembly | — |
| 80 | Final Test | **FPI** · QA sign-off · **sampling** · decision |
| 90 | Packaging | — |
| 100 | Complete | terminal (COMPLETED) |
| 110 | Rework | rework loop (failed parts route here; max visits enforced) |
| 120 | Nitride Coating | outside processing (OSP) |

- **Decision** steps route Pass/Fail; a **Fail** sends the part to **Rework**
  (op 110), which loops back until it passes or hits the visit cap ("Max
  Exceeded").
- **FPI** = first part off the step is bought off by QA before the batch runs.
- **Sampling** = a sampling plan selects which parts QA inspects (rest pass
  through); tightens/relaxes on the failure history.
- **Nitride Coating** is the outside-processing branch — parts ship to a
  subcontractor and are re-inspected on return.

---

## The 8 parts — pre-staged state

Each part is parked at exactly the state its walkthrough section needs.

| Part | Step | Status | What it stages | Walk |
|---|---|---|---|---|
| `INJ-QA-INSPECT-001` | Nozzle Inspection | IN_PROGRESS | Pending **FPI**, first-piece designated (first-piece substeps pre-signed by the operator) | §3 |
| `INJ-QA-INSPECT-002` | Nozzle Inspection | AWAITING_QA | **Sampled** ("post-repair verification"); 1 prior rework pass | §4 |
| `INJ-QA-INSPECT-003` | Flow Testing | IN_PROGRESS | Fresh, ready for a live measurement-driven **FAIL** → auto-quarantine + auto-disposition | §5 (→ §6) |
| `INJ-QA-INSPECT-004` | Flow Testing | AWAITING_QA | Visit 2: a historical FAIL QR + a CLOSED REWORK disposition already on file, ready for **re-inspection** | §7 |
| `INJ-QA-INSPECT-005` | Nitride Coating | AWAITING_QA | RETURNED from the OSP vendor (Apex Plating), awaiting **return inspection** (shipment `OSP-2026-000003`) | §8 |
| `INJ-QA-INSPECT-006` | Assembly | QUARANTINED | A bare OPEN NCR (`DISP-QAI-006-OPEN`) assigned to the inspector — the home/Control-page background exhibit | §1 (background), §6a |
| `INJ-QA-INSPECT-007` | Cleaning | IN_PROGRESS | Filler — not walked | — |
| `INJ-QA-INSPECT-008` | Disassembly | IN_PROGRESS | Filler — not walked | — |

Auto-generated record numbers (`DISP-2026-####`, `QR-2026-####`,
`OSP-2026-####`) are assigned by sequence and **shift on each reseed** — don't
key training material to the exact number; key to the part and the section.

---

## Demo logins

All demo users share the password **`demo123`**.

| Email | Name | Role | Used for |
|---|---|---|---|
| `sarah.qa@demo.ambac.com` | Sarah Chen | QA Inspector | The walker — §1–§12 |
| `maria.qa@demo.ambac.com` | Maria Santos | QA Manager | The gates Sarah hands up — §13 (the manager's whole side); the co-sign/approval gates in §6 (disposition) and §9 (CAPA); and authoring in §14 |
| `mike.ops@demo.ambac.com` | Mike Rodriguez | Operator | §3 — his signatures are pre-seeded on the first-piece substeps (not logged into) |

---

## Other work orders the walkthrough mentions in passing

These aren't walked; they exist so the home page and audit-trail sections look
like a real shop rather than a single-WO sandbox.

| Work order | Where it shows up |
|---|---|
| `WO-2024-0048-A` | The *other* pending-FPI row in the home "First piece waiting" banner (§1) |
| `WO-2024-0042-A` | An in-process Final Test row in the inbox. Two of its parts are borrowed as read-only exhibits where WO-QA-INSPECT-01 stages no equivalent: `INJ-0042-023` (SCRAPPED — the closed-record exhibit; walkthrough §12b and the training script's Journey 11) and `INJ-0042-019` (REWORK_IN_PROGRESS — the rework-in-flight exhibit; training script Journey 11). |
| `WO-2024-0038-A` | A completed storyline behind some seeded dispositions (§1 background) |

---

## Resetting

`cd PartsTracker && python manage.py seed_demo` restores every part above to
the state shown here (and re-arms the CAPA/approval exhibits §9/§13 use). Run it
before a training session, and again after any destructive walk-through so the
next run starts clean.
