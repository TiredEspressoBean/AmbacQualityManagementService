# Operator Guide

This guide is for production floor operators who move parts through manufacturing steps and record production data in uqmes.

!!! tip "Demo Account"
    In demo mode, log in as **Mike Rodriguez** (mike.ops@demo.ambac.com) to work
    the operator surface against a seeded queue.

    Which parts are waiting, and at which steps, changes every time the demo is
    reseeded or anyone walks it — so follow what Home actually shows you rather
    than looking for a particular serial.

## Your Role

As an Operator, you:

- Move parts through production steps
- Record measurements and data
- Flag issues when problems occur
- Track work order progress
- Use equipment for operations

## Getting Started

### First-Time Setup

1. Log in with credentials from your admin
2. Review the [Navigation Tour](../getting-started/navigation.md)
3. Familiarize yourself with the Tracker

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Home** | Home | **Your queue** — Up next, Then, In progress, and the scan box |
| **Work Orders** | Production > Work Orders | A job's whole picture, when you need it |
| **Inbox** | Personal > Inbox | CAPA tasks and notifications (if assigned) |

## Daily Workflow

### 1. See what is next

**Home is your queue.** It shows **Up next**, **Then** and **In progress**, plus
*See everything ready* — you do not have to be told what to work on, and you do
not start from the Work Orders page.

Shift notes and notifications land here too. A note marked **MUST ACKNOWLEDGE**
wants a **Got it** before you start; it is how the last shift talks to you.

Home also keeps you posted without asking anyone:

- **Your first pieces** — one line each while QA has it (*Not seen yet* or *Seen
  by*), then *Passed by*, *Failed by* or *Waived by* for the rest of the day.
- **Today** — the steps you've completed and the parts you've flagged for QA.
- **This week** — beside the clock: hours on shift, on jobs (and rework), and
  entries awaiting a lead's approval.

### 2. Find Your Work Order

**Fastest: use the scan box on Home.** It reads *"Scan or type a work order,
serial, lot or location…"* — scan the thing in your hand and it opens.

It takes more than work orders:

| Scan or type | Opens |
|--------------|-------|
| A **work order** number | That work order |
| A **serial** on a part or WIP tag | Its work order, with **Start work on parts** open and that unit ticked |
| A **lot number** | That material lot |
| A **location label** (the barcode reads `LOC:…`) | That location |
| The **QR code** on any printed label | Whatever it points at |

!!! tip "Scan the unit, not the paperwork"
    Scanning the serial ticks the exact unit in Start Work, which is the one
    thing a work-order number can't tell you. On a job with twenty units in flight it is
    the difference between the right part and a plausible one.

Or navigate by hand:

1. Navigate to **Production** > **Work Orders**
2. Search or filter to find the work order
3. Click to open the work order detail
4. Review parts at your step

See [Scanning](../workflows/supply/locations.md#scanning) for scanner setup.

### 3. Claim the parts you'll work

From the work order, click **Start Work**. The **Start work on parts** dialog
asks you to check the parts you'll do *in the order you'll do them*, then opens
the step player on the first one.

After you complete a part's step, **the player moves to the next part you
checked automatically** — so you work a batch without going back to the work
order. When you finish the last one, it returns you to the work order.

!!! note "If a part is already claimed"
    Starting a part assigned to someone else raises a gate naming who has it. A
    supervisor can sign in on your screen to reassign it — recorded against
    their name, not yours. That is normal, not an error.

## Moving Parts Forward

**There is no "Pass" button.** Parts advance automatically once the work at a
step is recorded. Your job is to complete the step; the system handles the
transition.

### Working a Step

Full detail: [Running Work Instructions](../workflows/dwi/running.md).

The step player shows **one substep at a time**:

1. Open the step's substeps for your part
2. Record what the substep asks for — a measurement, a check, a signature
3. Tap **Confirm & next** to seal that substep and move to the next one
4. At the end you get a **review screen** showing everything you recorded —
   jump back to fix anything that looks wrong
5. Tap **Complete step**

Once the step is complete and its requirements are satisfied, the parts move
forward on their own.

!!! tip "Parts move as a lot"
    Parts that have not been split advance together: all parts at the same work
    order and step move on, or none of them do. If parts seem stuck, it is
    usually because one part in the lot still has outstanding work.

!!! note "First Piece Inspection can hold the step"
    If the step has a pending First Piece Inspection, advancing is blocked for
    every part at that step until the FPI is signed off. **Complete step** stays
    put — it commits your captures. A separate sign-off button appears next to it
    for whoever is authorised to buy the first piece off.

### Quick Tips

- Complete steps promptly — a lot cannot advance until every part is done
- Never guess a value. If a required substep can't be done, stop and tell your
  supervisor
- Check the review screen before completing; it is the last easy place to fix
  a mistyped measurement

## Recording Measurements

When your step requires measurements:

### Recording Values

Measurements are captured as substeps inside the step player, not from a
separate "Record Measurements" button:

1. Work through the step's substeps until you reach a measurement capture
2. Enter the measured value
3. The system evaluates it against the specification automatically
4. Tap **Confirm & next**

### Reading Pass/Fail

As you enter a value, the capture reads **In spec** or **Out of spec** against
the specification. There is no "near the limit" warning — only those two.

### If a reading is out of spec

1. **Re-measure before you confirm.** Until you tap **Confirm & next**, the value
   is still yours to change
2. If it really is out of spec, confirm it — **do not adjust it to pass**

What happens next depends on the substep:

- At an **inspection point**, confirming an out-of-spec reading fails the
  quality report, which **quarantines the part and opens a disposition by
  itself**. You do not flag it separately
- Anywhere else, the reading is recorded as process data — it feeds SPC — and
  nothing is quarantined. If you think the part is bad, **tell your lead** or
  quarantine it from the parts list

## Flagging Issues

There is **no Flag button on a part**. Where a problem goes depends on where
you find it:

- **Working the step** — record the result on the inspection-point substep in
  the step player. That writes the quality record for you.
- **Part already past the step** — tick it in the work order's parts list and
  click **Quarantine**.
- **A machine is down** — open the work order and click **Report…**, then
  **Downtime**.
- **Bigger than one part** — raise a disposition or a CAPA; **Report…** links
  to both forms.

See [Flagging Issues](../workflows/tracking/flagging-issues.md) for the full
procedure and when to use each.

### If you can't run the job at all

**Can't run this?** on Home isn't in use yet. Missing material, a broken fixture
or anything else that stops the job: go to your lead and tell them.

### When to Flag

- Part doesn't meet visual standards
- Measurement out of tolerance
- Damage discovered
- Process deviation occurred
- Anything that seems wrong

!!! tip "When in Doubt, Flag It"
    It's better to flag a potential issue than let a bad part continue.

## Using Equipment

Where a substep captures equipment, record the gauge or machine you actually
used. It is kept against the measurement, which is what lets quality answer
*"what else did this gauge measure?"* if it later fails a calibration check.

### Calibration — the system handles it, you don't have to remember

A gauge whose calibration **failed**, or that is out of service, **cannot be
used to capture a measurement**. The capture is refused outright: *"Recalibrate
or pick a different gauge."* Get a different one and tell your lead — the gauge
is the problem, not your reading.

A gauge that is merely **overdue** is different. The reading is **recorded** and
you are told, because an overdue check is a scheduling lapse rather than
evidence the gauge is wrong. Don't ignore the warning, but your work is not
lost.

Nobody can quietly put a failed gauge back into service either: returning
equipment to service is refused until a *passing* calibration is recorded
against it.

## Work Orders

### Viewing Work Order Details

1. Navigate to **Production** > **Work Orders**
2. Find your assigned work order
3. See parts by step
4. View work instructions

### Accessing Work Instructions

**The work instructions are the step player.** There is no separate document to
open and follow alongside the job — the substeps you work through *are* the
instruction, and what you record in them is the quality record.

Documents attached to the job — a drawing, a spec, a customer requirement — are
reference material. Useful to consult, but they are not where the procedure
lives.

## First Piece Inspection (FPI)

If FPI is required at your step:

### The Process

1. **Start FPI** from the banner — this designates the first piece and holds
   the run
2. Run that part's work instruction as normal and **Complete step** — its own
   captures *are* the inspection
3. QA buys it off. There is nothing to submit and nothing queues for review:
   finishing the captures is what makes it ready
4. Once it passes, the whole step is released and the batch continues

!!! tip "You don't have to go and find QA"
    Once the first piece is ready, a **Get QA sign-off** button appears beside
    **Complete step**. An authorized inspector signs **at your station** with
    their email and password — you stay logged in, and the buy-off is recorded
    against them.

### While Waiting

- Other parts are held automatically
- Continue setup verification
- Don't proceed until FPI passes

## End of Shift

### There is nothing to hand over

Work is batched and nobody stops half way through a part. You finish the units
you finish; whoever is on next picks up the rest of the batch. **Each part
carries its own record with its own name on it**, so a batch worked by two
people across a shift change is a hundred attributed records, not a transfer.

There is no "hand over" action, and there is nothing to update to say you have
stopped — because nothing was ever held open in your name.

### What does matter before you go

- **Complete any step you actually finished.** A lot cannot advance until every
  part in it is done, so an uncompleted step of yours holds up everyone else's.
- **Submit, don't leave drafts.** Confirming a substep saves it as a draft;
  until you tap **Complete step** nothing is official and the part has not
  moved.
- **Tell your lead about anything you couldn't run**, rather than leaving it for
  the next person to rediscover.

## Common Tasks Quick Reference

| Task | Steps |
|------|-------|
| Move part forward | Complete the step — advancement is automatic |
| Record measurement | Step player → measurement substep → enter value → **Confirm & next** |
| Substep can't be done | Stop and tell your supervisor; required substeps can't be skipped |
| Finish a step | Step player → review screen → **Complete step** |
| Flag issue | In the player: record it on the inspection substep · Otherwise: tick the part → **Quarantine** |
| Can't run the job | Tell your lead |
| View instructions | They are the step player's substeps — there is no separate document to open |

## What You CAN'T Do

These are withheld from the Operator role and enforced on the server:

| Not yours | Who holds it |
|-----------|--------------|
| **Approve a disposition** | QA Manager |
| **Sign off a first piece** | Shift Lead, QA Inspector, QA Manager, Production Manager |
| **Resolve a manual decision point** | Shift Lead, QA, Production Manager |
| **Initiate a CAPA** | Shift Lead, QA, Production Manager, Purchasing, Receiving |
| **Verify a CAPA worked** (which is what closes it) | QA Manager |
| **Void a substep completion** | QA Inspector, QA Manager, Tenant Admin |
| **Write a training record** | Shift Lead, QA Manager, Production Manager, Engineering, Document Controller |
| **Release a torn-down core, send it for the customer's authorisation, or complete its teardown by hand** | Shift Lead, Production Manager, Planner, Tenant Admin |
| **Manage users** | Tenant Admin |

These are the default groups an organisation starts with. Group permissions can be changed, so check your own in [Roles & Groups](../admin/users/roles.md).

!!! note "You can do more than you might expect"
    The shared staff base is broad: an Operator **can** create orders and work
    orders, upload documents, and raise a quality report. Whether you *should*
    is your shop's procedure, not a permission.

    On a remanufactured core you work its teardown and rebuild steps as usual;
    finishing the teardown route closes the teardown on its own. Releasing the
    torn-down unit is your lead's call: the work order's **Cores** card reads
    *A lead releases it*, and the core's page *Torn down — a lead releases it*.

### If you recorded something wrong

**You cannot undo your own completion, and that is deliberate** — performing the
work and adjudicating the record are different jobs.

- **Before you finish the step**, the review list is the last easy place to fix
  a mistyped measurement. Read down it.
- **After it is recorded**, ask a **QA Inspector** or **QA Manager** to void the
  completion. They record why, the advancement gate ignores the voided row, and
  the part waits until the work is redone.

Nothing is deleted — the original record and the void both stay. See [Voiding a
completion](../workflows/dwi/running.md#voiding-a-completion).

- **A part moved on too soon**, the **wrong part loaded into a cycle**, or **your
  clock times are wrong**: tell your shift lead. Those corrections are theirs.

Everything that can be put right, and who does it, is on [Putting a Mistake
Right](../workflows/fixing-mistakes.md).

## Troubleshooting

### "Cannot move forward"

Check for:
- Required substeps or measurements not recorded
- A QA sign-off the step needs, not given yet
- FPI required but not passed
- Another part in the lot still has outstanding work — the lot moves together
- Part in quarantine, **where the step is set to block on quarantine** — most
  steps are not, so a quarantined part often keeps moving

### "Permission denied"

- You may not have access to this action
- Contact supervisor or admin

### Part not showing

- Check filters on Work Orders page
- Verify correct work order
- Part may be at different step

## Getting Help

- **Your Supervisor**: Process questions, permissions
- **Quality**: Measurement issues, defects
- **IT/Admin**: Login issues, system problems

## Related Documentation

- [Tracker Overview](../workflows/tracking/tracker-overview.md)
- [Moving Parts](../workflows/tracking/moving-parts.md)
- [Recording Measurements](../workflows/tracking/measurements.md)
- [Flagging Issues](../workflows/tracking/flagging-issues.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
