# The Shop Day

One working day at the training shop, with every role's moments in it. The moments
connect: the first piece one person runs is the first piece the next person buys
off, and the defect that turns up at 10:00 is the CAPA raised at 12:00.

Each role's track is its slice of this day, so tracks compose: an inspector and a
shift lead taking their own tracks are working the same Tuesday. Every name and
record here is one the training instance's seed creates.

## The shop

The shop builds new **common rail injectors** and remanufactures used ones, on two
separate routes:

- **Injector Build**, new manufacture: the body is machined from bar stock,
  ground, washed and inspected, nitrided at the plater, assembled with a purchased
  nozzle and control valve, flow-calibrated, tested, marked and shipped.
- **Injector Reman**: used units come in as **cores**, are torn down, graded,
  cleaned, inspected and rebuilt. This route is in the [reman
  additions](#if-your-shop-remanufactures), not the base day.

Nitride coating goes out to a plating subcontractor. The shop is small enough that
people hold more than one role.

### The cast

| Person | Role | Login |
|--------|------|-------|
| Jennifer Walsh | Production Manager | `jennifer.mgr@demo.ambac.com` |
| Sam Okafor | Planner | `sam.plan@demo.ambac.com` |
| Casey Cross | Shift Lead, and an inspector when covering | `casey.dual@demo.ambac.com` |
| Mike Rodriguez | Operator | `mike.ops@demo.ambac.com` |
| Dave Wilson | Operator whose certification has lapsed | `dave.wilson@demo.ambac.com` |
| Sarah Chen | QA Inspector | `sarah.qa@demo.ambac.com` |
| Maria Santos | QA Manager | `maria.qa@demo.ambac.com` |
| Lisa Park | Document Controller | `lisa.docs@demo.ambac.com` |
| Jordan Reyes | Engineering | `jordan.eng@demo.ambac.com` |
| Priya Nair | Purchasing | `priya.buy@demo.ambac.com` |
| Luis Ortega | Receiving | `luis.recv@demo.ambac.com` |
| Rosa Kim | Shipping | `rosa.ship@demo.ambac.com` |
| Alex Morgan | Auditor | `alex.audit@demo.ambac.com` |
| Tom Bradley | Customer contact at Midwest Fleet Services | `tom.bradley@midwestfleet.com` |

Every password is `demo123`.

**The companies:**

| Company | Is |
|---------|----|
| Midwest Fleet Services | The customer whose repair runs through the day |
| Great Lakes Diesel | A customer, and the supplier of most purchased lots received at the dock |
| Northern Trucking Co | Another customer |
| Apex Plating Co | The nitride-coating subcontractor, qualified for nitriding |
| Lakeshore Seals Inc | A seals supplier whose qualification has lapsed |
| Precision Castings Inc, Midwest Forge Works, Bargain Bolts LLC | Material suppliers, at different stages of qualification |

## The day

### 06:00 — Sam reads the board

The schedule is stale. They re-solve, and the solve can't staff a gated step. They
open **Pull in work** and admit work against the recommendation.

> **Track:** Planner. **Opens:** the labour gap Casey decides at 07:30.

### 06:30 — A delivery reaches the dock

Several lots arrive against expected receipts. One fails incoming inspection and is
held.

> **Track:** Receiving. **Opens:** Purchasing at 07:00, and the shortage
> Jennifer plans around at 14:30.

### 07:00 — Purchasing chases, and raises a SCAR

The held lot is the supplier's second rejection, so Purchasing raises a supplier
corrective action request. A separate late delivery gets chased.

> **Track:** Purchasing.

### 07:30 — Casey starts the shift

Mike is the only operator free for Body Inspection, and Mike's inspection
certification doesn't cover it. Casey decides to let the work start on Casey's
own authority.

> **Track:** Shift Lead. **Closes:** Sam's 06:00 labour gap. **Opens:** the
> training record Maria writes at 15:30.

### 08:00 — Mike runs the first piece

Mike starts Body Inspection on `WO-QA-INSPECT-01`. The training gate refuses
the start, and Casey authorises it at Mike's terminal with a reason. Mike runs
the first piece, `INJ-QA-INSPECT-001`, and the run holds for a first-piece buy-off.

> **Track:** Operator. **Opens:** Sarah's buy-off at 08:30.

### 08:30 — Sarah buys off the first piece

Sarah reads the first piece's readings (Bore Diameter inside 3.995–4.005, taken
by Mike) and signs it off. The run moves. Two other runs are waiting on first
pieces too: one to fail, and one that repeats yesterday's setup and is waived. A
third first piece's inspection was Sarah's own, so Casey signs it at Sarah's
screen.

> **Track:** QA Inspector. **Closes:** Mike's 08:00 hold.

### 09:00 — A sampled part comes to Sarah

`INJ-QA-INSPECT-004` waits behind the first piece, and its history says why it was
picked: *Selected by every 4th part*. One gauge on the inspection's list is greyed
out: `Micrometer MIC-2` failed its calibration this morning.

> **Track:** QA Inspector.

### 09:30 — What arrives

The incoming queue holds a purchased lot to inspect, `RCV-MAT-0002`, and a held lot,
`RCV-MAT-HOLD`, from Bargain Bolts LLC: missing its heat number and from an
unqualified supplier. Shipment `OSP-2026-000002` is back from Apex
Plating Co, and the return needs inspecting before it rejoins the line.

> **Track:** QA Inspector. **Closes:** the 06:30 delivery, for the lots it inspects.

### 10:00 — A reading goes out of spec

At Flow Calibration, `INJ-QA-INSPECT-012` reads 95 mL/min against limits of 100–140.
Nobody decides it failed: the spec does. The part is quarantined and a disposition
opens, unassigned, in the QA queue.

> **Track:** Operator and QA Inspector. **Opens:** the disposition at 11:00.

### 10:30 — Sarah marks the defect

Yesterday's visual inspection failed `INJ-QA-INSPECT-015` at Body Inspection for a
burr in the bore, a defect that must be marked on the part's 3D model. Sarah takes
its disposition from the queue and marks the burr on the model; until then, the
disposition can't close.

> **Track:** QA Inspector.

### 11:00 — The disposition

Sarah records containment on the 10:00 failure and decides **Rework**. Sarah
doesn't hold the authority, so Maria co-signs at Sarah's terminal, and the decision
is recorded under Maria's name.

> **Track:** QA Inspector and QA Manager. **Closes:** the 10:00 failure.

### 11:30 — Sarah re-inspects a reworked part

`INJ-QA-INSPECT-013` failed at Flow Calibration yesterday and waits at Rework. Sarah reads
its history, the failed reading, the decision and who authorised it, before
inspecting it again.

> **Track:** QA Inspector.

### 12:00 — Casey makes the calls

A manual decision point is waiting for a person, and the same defect has now
turned up repeatedly. Casey resolves the decision point and raises a CAPA.

> **Track:** Shift Lead. **Opens:** the process change at 13:00.

### 13:00 — Engineering changes the process

The CAPA's cause is in the process. Engineering drafts a new version of it and
submits it for approval.

> **Track:** Engineering. **Opens:** Lisa's revision at 13:30 and
> Maria's approval at 14:00.

### 13:30 — Lisa revises the work instruction

The controlled document that goes with the step needs a revision. Lisa creates
it, writes the reason, and submits it for approval.

> **Track:** Document Controller.

### 14:00 — Maria approves

The process change and the document revision are both waiting for Maria.

> **Track:** QA Manager. **If your organisation runs change control in
> Simplified mode**, the process change is approved in one step. See [Change
> Control](../workflows/change-control/overview.md#simplified-or-regulated).

### 14:30 — Jennifer re-promises

Great Lakes Diesel's order `ORD-2024-0051` asks for 6 new injectors in three weeks.
Jennifer checks capacity on its line before promising.

> **Track:** Production Manager. **Closes:** the 06:30 shortage.

### 15:00 — Jennifer takes the order

Jennifer plans the order's line into a work order, which creates its parts, and
releases it.

> **Track:** Production Manager.

### 15:30 — Maria writes Mike's training record

Casey's override this morning was the right call, but not something to repeat
every shift. Maria records Mike's dimensional inspection certification, and the gate stops
refusing Mike.

> **Track:** QA Manager. **Closes:** Casey's 07:30 decision.

### 17:00 — The day's work ships

Finished work orders ship with their paperwork.

> **Track:** Shipping.

### 17:30 — Casey hands over

Casey writes the shift note for the next shift: the held lot, the open CAPA and
Mike's certification.

> **Track:** Shift Lead.

### Through the day — the auditor and the customer

The **auditor** follows the day backwards from the CAPA: the report, the
disposition and its containment, and who signed what. Tom Bradley at Midwest
Fleet Services sees their own orders and nothing else, and can answer an approval
request the shop sends them.

> **Orientation:** Auditor and Customer.

## If your shop remanufactures

These moments are on the **Injector Reman** route, and each track's reman addition
covers them. A shop that only builds new skips this section.

Used units come in as **cores**. Some customers send their own unit for **repair
and return**; others take a rebuilt unit from stock in **exchange** for theirs.

### 16:00 — A customer's core comes in

A Midwest Fleet Services unit arrives for repair and return, is torn down, and
waits on its release decision. Being the customer's own, it can only be rebuilt
and returned, never harvested.

> **Track:** Receiving and Shift Lead, reman additions.

### 16:30 — Harvested components

A core torn down as a parts source yields components graded A to scrap. QA accepts
the good ones into stock and scraps the rest.

> **Track:** QA Inspector, reman addition.

### 17:00 — The rebuilt repair ships

A rebuilt repair goes back to its owner on its own shipment.

> **Track:** Shipping, reman addition.

## The interlocks

| Opened | Closed | What connects them |
|--------|--------|--------------------|
| 06:00 Sam's solve can't staff a step | 07:30 Casey decides, 08:00 the authorisation | The planning gap is a person without a certification |
| 07:30 Casey's override | 15:30 Maria's training record | An override is a decision, not a fix |
| 06:30 a lot is held | 07:00 the SCAR, 14:30 Jennifer's promise | A dock decision is a supplier fact and a planning constraint |
| 08:00 Mike's first piece | 08:30 Sarah's buy-off | The run waits for a second person's judgement |
| 10:00 the out-of-spec reading | 11:00 Maria's co-sign | A finding reaches the authority without a handoff |
| 12:00 Casey's CAPA | 13:00–14:00 the change, the revision, the approval | A repeated defect is a process problem, and a process change brings its document with it |
