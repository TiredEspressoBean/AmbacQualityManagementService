# CAPA Tasks

CAPA tasks are action items assigned to team members to complete the investigation and corrective actions.

## Task Types

| Task Type | Purpose |
|-----------|---------|
| **Containment** | Immediate actions to limit impact |
| **Corrective Action** | Actions to fix the problem and address root cause |
| **Preventive Action** | Systemic changes to prevent recurrence |

There are only these three, and the type is a label — **nothing behaves
differently because of it**. It tells a reader which kind of action they are
looking at; it does not change ordering, gating or closure.

Root cause analysis is not a task. It is tracked separately as an RCA record
linked to the CAPA — see [CAPA Overview](overview.md).

## Creating Tasks

### From CAPA Detail

1. Open the CAPA
2. Go to **Tasks** tab
3. Click **Add Task**
4. Complete the form:

| Field | Description |
|-------|-------------|
| **Description** | What the task is |
| **Type** | Containment, Corrective Action, or Preventive Action — there are only these three |
| **Assigned To** | The owner |
| **Assignees** | Additional people, when more than one person is involved |
| **Completion Mode** | Who has to complete it — see below |
| **Due Date** | Target completion |
| **Requires Signature** | Completion needs a signature and password verification |

Tasks are numbered automatically.

5. Click **Save**

!!! note "No task templates"
    There is no **Add Standard Tasks** action and no library of task templates
    to apply to a CAPA type. Tasks are added one at a time.

## Task Status

| Status | Meaning |
|--------|---------|
| **Not Started** | Task created but not yet begun |
| **In Progress** | Actively being worked |
| **Completed** | Task finished |
| **Cancelled** | No longer needed |

### Completion Mode

Tasks can have different completion requirements:

| Mode | Description |
|------|-------------|
| **Single Owner** | One person completes the task |
| **Any Assignee** | Any one assignee can complete for the group |
| **All Assignees** | All assigned users must complete their portion |

### Signed completion

A task can be marked **Requires Signature**. Completing it then needs a
signature and password verification, and the record keeps the signature, who
completed it, when, and their completion notes.

Use it for tasks whose completion is itself evidence — a verification step, or
an action someone must attest to personally. See [Electronic
Signatures](../../compliance/signatures.md).

## Working on Tasks

### Viewing Your Tasks

1. Navigate to **Personal > Inbox**
2. See all assigned tasks
3. Filter by status, CAPA, due date

### Starting a Task

1. Open the task
2. Click **Start** or change status to In Progress
3. Add notes as you work

### Completing a Task

A task can be completed from either surface — whichever you are already on:

- **Personal > Inbox**, against the task in your list
- The CAPA's **Tasks** tab

In both, **Complete Task** opens a dialog for your completion notes; confirm it
with **Complete Task** in the Inbox or **Mark Complete** on the Tasks tab.
Completing is done only this way: the task's edit form doesn't offer
**Completed**, and a completed task can't be reopened. The notes are
saved with the completion, so say what was actually done rather than "done" —
this is the record a verifier reads when checking the action was effective.

If the task **requires a signature**, completing it asks for your password as
well. See [Signed completion](#signed-completion).

!!! note "Completion mode decides whether that finishes it"
    On a task with several assignees, whether your completion closes the task
    or only records your part of it depends on its completion mode. See
    [Completion Mode](#completion-mode).

## Task Evidence

A task has no attachments of its own. Evidence (photos, updated procedures,
data, investigation reports) goes on the CAPA's **Documents** tab, where it's
kept with the CAPA. Say in your completion notes which documents show the task
was done.

## Task Notifications

Notifications are **rule-driven and configurable** — who gets told what is
decided by this tenant's notification rules, not by the event itself. Any rule
can be edited, disabled or deleted, so treat routing as something to check
rather than something to rely on. See [Notification
Rules](../../admin/setup/notification-rules.md).

Two CAPA rules ship by default: the **assignee** is notified when a CAPA is
assigned or reassigned, and **QA Manager** when a CAPA becomes ready for
effectiveness verification. A task's assignee is also emailed when the task is
created or reassigned to them. Other task-level alerts (an overdue task, say)
aren't seeded: if you need them, write the rule.

## Task Due Dates

A task past its due date shows a red **Overdue** badge on the CAPA's **Tasks**
tab, with its date in red. There is no earlier warning colour and no automatic
escalation; an overdue task notifies nobody unless you write a rule for it.

!!! important "Open tasks block closure"
    A CAPA closes when its effectiveness is confirmed, and that is refused while
    any task is still open: *"Cannot close CAPA: N task(s) still pending. Complete
    them before confirming effectiveness."* Overdue or not, every task has to be
    completed or cancelled first. A cancelled or deleted task doesn't count, and
    a cancelled task is left out of the completion percentage.

The task list can be filtered to **overdue only**, which is the quickest way to
see what is actually holding a CAPA open. Note this is the task-level filter —
filtering *CAPAs* by overdue tells you which CAPAs are late overall, not which
tasks inside them are.

## Reassigning Tasks

There is no Reassign action. Reassignment is a plain edit of the task:

1. Open the task
2. Change **Assigned To**
3. Save

The new assignee is emailed, as when a task is first assigned; the old one
isn't told. Saving the task with the same assignee sends nothing. There is no
reassignment reason to record. The change is in the audit trail.

## Task Metrics

Track task performance:

| Metric | Description |
|--------|-------------|
| **Tasks by status** | Distribution |
| **Overdue tasks** | Count and age |
| **Average completion time** | Efficiency |
| **Tasks per CAPA** | Workload indicator |

## Your Tasks in Inbox

The **Personal > Inbox** page shows:

- All tasks assigned to you
- Grouped by CAPA
- Sorted by due date
- Quick actions (start, complete)

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_capatasks` | View tasks | Every staff role |
| `add_capatasks` | Create tasks | Every staff role |
| `change_capatasks` | Edit and **complete** tasks | Every staff role |
| `delete_capatasks` | Remove a task outright | Manager tier — QA Manager, Production Manager, Document Controller, Tenant Admin |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

Working CAPA tasks is deliberately open: anyone on the team can be given one and
complete it. **Deleting** one is not, because a task that was raised and then
removed is a hole in the investigation record. If a task is no longer needed,
set it to **Cancelled** rather than deleting it — that keeps the decision
visible.

## Next Steps

- [Verification & Closure](verification.md) - Completing the CAPA
- [Creating a CAPA](creating.md) - Initial setup
- [CAPA Overview](overview.md) - Process reference
