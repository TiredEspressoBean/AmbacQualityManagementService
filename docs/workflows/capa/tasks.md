# CAPA Tasks

CAPA tasks are action items assigned to team members to complete the investigation and corrective actions.

## Task Types

| Task Type | Purpose | Phase |
|-----------|---------|-------|
| **Containment** | Immediate actions to limit impact | D3 |
| **Corrective Action** | Actions to fix the problem and address root cause | D5, D6 |
| **Preventive Action** | Systemic changes to prevent recurrence | D7 |

Note: Root cause analysis is tracked separately via RCA records linked to the CAPA.

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
4. Attach evidence

### Completing a Task

1. Open the task
2. Add completion notes
3. Attach deliverables (documents, data)
4. Click **Complete**
5. Task moves to Complete status

## Task Dependencies

Tasks can depend on other tasks:

1. Edit the task
2. In **Blocked By** section
3. Select prerequisite tasks
4. Task cannot start until dependencies complete

Example:
- "Implement corrective action" blocked by "Get approval for fix"

## Task Evidence

Attach evidence of completion:

- **Photos**: Before/after images
- **Documents**: Updated procedures
- **Data**: Measurement results
- **Reports**: Investigation reports

1. Open the task
2. Go to **Attachments**
3. Upload files
4. Files are linked to CAPA record

## Task Verification

For critical tasks, verification may be required:

1. Assignee completes task
2. Task goes to **Pending Verification**
3. Verifier reviews completion
4. Verifier approves or returns
5. Task marked **Verified** or back to **In Progress**

## Task Notifications

| Event | Recipients |
|-------|------------|
| Task assigned | Assignee |
| Task approaching due | Assignee |
| Task overdue | Assignee, CAPA owner |
| Task completed | CAPA owner |
| Task needs verification | Verifier |

## Task Due Dates

Due dates drive urgency:

| Indicator | Status |
|-----------|--------|
| **Green** | On track |
| **Yellow** | Due within 3 days |
| **Red** | Overdue |

Overdue tasks:

- Appear on dashboard
- Trigger escalation (if configured)
- Block CAPA closure

## Reassigning Tasks

If someone can't complete a task:

1. Open the task
2. Click **Reassign**
3. Select new assignee
4. Add reassignment reason
5. Original assignee notified

## Task Comments

Collaborate on tasks:

1. Open the task
2. Scroll to **Comments**
3. Add comment
4. Tag users with @mention
5. Comments visible to team

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

## Bulk Task Actions

For multiple tasks:

1. Select tasks (checkboxes)
2. Choose bulk action:
   - Mark complete
   - Reassign
   - Change due date

## Permissions

| Permission | Allows |
|------------|--------|
| `view_capatasks` | View tasks |
| `add_capatasks` | Create tasks |
| `change_capatasks` | Edit, complete tasks |
| `delete_capatasks` | Remove tasks |

## Next Steps

- [Verification & Closure](verification.md) - Completing the CAPA
- [Creating a CAPA](creating.md) - Initial setup
- [CAPA Overview](overview.md) - Process reference
