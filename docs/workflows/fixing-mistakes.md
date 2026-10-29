# Putting a Mistake Right

Everyone keys something wrong sooner or later. This page lists the common
mistakes, what puts each one right, and who can do it. Each row links to the page
that explains it.

!!! important "How corrections work in uqmes"
    - **Nothing is deleted.** A correction is a new, recorded act beside the
      original. A voided capture stays struck through, a reopened record keeps
      its closing, a withdrawn answer stays in the history.
    - **A correction asks why.** The reason is kept with the change, so the
      record answers *what, who, when* **and** *why*. Most appear under
      **Corrections** in the record's history.
    - **Some things are final on purpose.** An applied count, a decided approval,
      a closed CAPA, a cancelled work order, an implemented process change. The
      way forward is a new record, not an edit of the old one, and the rows below
      say which.
    - **Correcting isn't always your call.** Voiding someone's capture, deciding a
      disposition, approving a late rollback: each needs the authority the
      original decision needed, so the person who made the mistake may need to
      ask someone else.

## On the floor

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| A reading keyed wrong, before **Complete step** | Fix it on the step player's review screen | Operator | [Recording Measurements](tracking/measurements.md#correcting-a-measurement) |
| A reading or check wrong after **Complete step** (wrong value, gauge or method) | **Void** the completion with a reason, then capture it again | QA Inspector, QA Manager | [Voiding a completion](dwi/running.md#voiding-a-completion) |
| Recorded against the wrong part | Void it on that part; capture on the right one | QA Inspector, QA Manager | [Capturing it again](dwi/running.md#capturing-it-again) |
| The step you just finished needs redoing | **Undo** on your Home page's last-finished line, with a reason — offered until someone finishes the next step; past the window or where the step needs approval, it goes to QA | Operator | [Operator](../roles/operator.md#if-you-recorded-something-wrong) |
| A part moved on too soon | **Previous step**, with a reason. It goes to QA for approval unless the step allows a direct rollback and it's within the step's window | Shift Lead | [Sending a part back a step](tracking/moving-parts.md#sending-a-part-back-a-step) |
| The wrong part loaded into a shared cycle | **Take this part out**, from the part's history | Shift Lead | [The wrong part in a shared cycle](tracking/moving-parts.md#the-wrong-part-in-a-shared-cycle) |
| A draw recorded against the wrong lot | **Wrong lot?** on that lot's page: move the draw to the lot used | Shift Lead and up | [A draw recorded against the wrong lot](tracking/lot-tracking.md#a-draw-recorded-against-the-wrong-lot) |
| Wrong clock-in or clock-out | **Correct times**, before approving | Shift Lead | [Approving time](scheduling/overview.md#approving-time) |
| Downtime recorded against the wrong machine or times | **Correct…** on the event in Exceptions | Shift Lead | [Downtime](../admin/setup/equipment.md#downtime) |
| A training override that shouldn't have been given | **Flag for QA review** on the override; the override itself stands | Shift Lead | [An override that shouldn't have been given](quality/training-records.md#an-override-that-shouldnt-have-been-given) |
| A work order held, or released, by mistake | **Resume** saying it was in error / **Un-release** | Shift Lead, Production Manager | [Undoing one by mistake](work-orders/progress.md#undoing-one-by-mistake) |
| A work order short-closed by mistake | **Reopen**, with a reason | Production Manager | [Short-closed by mistake](work-orders/basics.md#short-closed-by-mistake) |
| A priority set wrong | Set it again; it asks why | Production Manager, Shift Lead | [Work Order Progress](work-orders/progress.md) |

## Quality

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| An inspection recorded FAIL that should have passed | Void it, re-inspect, then close the disposition as **Not a nonconformance** | QA Inspector, then QA Manager | [When the finding was wrong](quality/dispositions.md#when-the-finding-was-wrong-not-a-nonconformance) |
| An inspection recorded PASS that should have failed | Void it and capture the FAIL | QA Inspector | [Voiding a completion](dwi/running.md#voiding-a-completion) |
| A first piece passed in error | **Void pass**: the run holds until it is re-inspected | QA Inspector | [A first piece passed in error](work-orders/fpi.md#a-first-piece-passed-in-error) |
| A disposition decided wrong | Decide again while it is open. A Scrap changed un-scraps, with a reason | QA Manager | [Decided wrong, or closed too soon](quality/dispositions.md#decided-wrong-or-closed-too-soon) |
| A disposition closed by mistake | **Reopen**, with a reason | QA Manager | [Decided wrong, or closed too soon](quality/dispositions.md#decided-wrong-or-closed-too-soon) |
| A CAPA verified wrongly | Before closing: Not Effective sends it back. A closed CAPA is final: raise a new one | QA Manager | [Closed is the end of the line](capa/verification.md#closed-is-the-end-of-the-line) |
| A training record wrong | Edit it; the form asks for a reason | QA Manager | [Correcting a record](quality/training-records.md#correcting-a-record) |
| A calibration result wrong | Edit it with a reason; the gauge status follows | QA Manager | [Correcting a calibration record](../admin/setup/equipment.md#correcting-a-calibration-record) |
| A supplier suspended by mistake | **Grant…** again. Disqualified is final: a new qualification | QA Manager | [Approved Suppliers](supply/overview.md#approved-suppliers) |

## Receiving and stock

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| Received quantity keyed wrong | **Correct receipt…**, while nothing has been taken | Receiving | [Correcting a receipt](supply/overview.md#correcting-a-receipt) |
| Wrong supplier, item, PO or line on a lot | **Correct receipt details**, while untouched | Receiving | [Correcting a receipt](supply/overview.md#correcting-a-receipt) |
| **That's all** chosen when more is coming | **Reopen the rest** | Receiving | [Answered That's all by mistake](supply/overview.md#answered-thats-all-by-mistake) |
| Marked posted to the ERP before keying it | **Unmark** | Receiving | [Marked one posted that wasn't keyed](supply/overview.md#marked-one-posted-that-wasnt-keyed) |
| A lot accepted that should have been rejected | **Reject remaining stock…**, or a concession on the disposition | QA Manager | [Who can reject a whole lot](supply/overview.md#who-can-reject-a-whole-lot) |
| Put away in the wrong place | **Move…** it again | Receiving | [Moving something](supply/locations.md#moving-something) |
| A cycle count that looks wrong | **Send back for recount**, before applying. Applied is final | Shift Lead and up | [A count that looks wrong](supply/locations.md#a-count-that-looks-wrong) |
| An expected delivery keyed wrong | **Cancel expected receipt…** with a reason, then add it again | Purchasing | [Cancelling something you are no longer expecting](supply/overview.md#cancelling-something-you-are-no-longer-expecting) |
| A shipment recorded by mistake, or the wrong quantity shipped | **Void…** with a reason, then ship again. A split lot rejoins its lot | Shipping | [After it has gone](supply/shipping.md#after-it-has-gone) |
| Wrong carrier or tracking | Edit the shipment's paperwork | Shipping | [After it has gone](supply/shipping.md#after-it-has-gone) |

## Remanufacturing

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| A core received under the wrong mode or order | **Correct receipt…**, while it is still Received | Receiving | [Step 2: Enter Core Information](reman/receiving.md#step-2-enter-core-information) |
| A component graded wrong at teardown | A **finding**, then **Apply** | Shift Lead | [Findings](reman/components.md#findings-a-component-found-worse-at-the-bench) |
| The customer's answer recorded wrong | **Correct customer's answer…**, until the repair starts | Production Manager, QA Manager | [Recording the answer](reman/disassembly.md#recording-the-answer) |
| The wrong component fitted | **Remove** on the *As built* card. A Rebuilt unit goes back to In Rebuild | Operator, Production Manager | [Fitted the wrong component](reman/rebuild.md#fitted-the-wrong-component) |

## Planning

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| A what-if committed by mistake | **Restore the previous plan** — one step back | Planner | [Committed one by mistake](scheduling/gantt.md#committed-one-by-mistake) |
| A task moved, or pinned, by mistake | **Undo** the last move; unpin a pin | Planner | [Undo](scheduling/gantt.md#undo) |
| A calendar entry made wrong | **Remove** it, add it again, re-solve | Planner | [Calendar](scheduling/overview.md#calendar) |

## Documents, approvals and change

| Mistake | What puts it right | Who | |
|---------|--------------------|-----|---|
| A document submitted with a mistake in it | **Withdraw request**; it goes back to Draft | The requester | [Withdrawing a request](documents/approval.md#withdrawing-a-request) |
| Answered an approval the wrong way | **Change my response**, while the request is open | The approver | [Changing your response](documents/approval.md#changing-your-response) |
| A document obsoleted by mistake | **Reinstate**, if no later revision replaced it | Document Controller | [Obsoleted by mistake](documents/library.md#obsoleted-by-mistake) |
| A process change implemented by mistake | A new change back, through change control | Engineering | [Implemented by mistake](change-control/overview.md#implemented-by-mistake) |
| A temporary change applied to the wrong work order | **Move back to baseline** | Engineering | [Temporary changes](change-control/overview.md#temporary-changes-deviations) |
| Someone given the wrong role, or suspended by mistake | Change their groups / **Activate** | Tenant Admin | [Deactivating Users](../admin/users/deactivating.md#removing-someones-access) |
