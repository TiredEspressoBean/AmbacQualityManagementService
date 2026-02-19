# CAPA Tasks

CAPA tasks are action items assigned to team members to complete the investigation and corrective actions.

## Task Types

| Task Type | Purpose | Phase |
|-----------|---------|-------|
| **Containment** | Immediate actions to limit impact | D3 |
| **Investigation** | Root cause analysis activities | D4 |
| **Corrective Action** | Actions to fix the problem | D5, D6 |
| **Verification** | Confirm actions were effective | D7, D8 |
| **Documentation** | Update procedures, records | D7 |

## Creating Tasks

### From CAPA Detail

1. Open the CAPA
2. Go to **Tasks** tab
3. Click **+ Add Task**
4. Complete the form:

| Field | Description |
|-------|-------------|
| **Title** | Clear action description |
| **Type** | Containment, Investigation, etc. |
| **Assigned To** | Responsible person |
| **Due Date** | Target completion |
| **Description** | Detailed instructions |
| **Priority** | Follows CAPA priority |

5. Click **Save**

### Bulk Task Creation

For standard CAPA types, create multiple tasks:

1. Click **Add Standard Tasks**
2. Select task template
3. Adjust assignments and dates
4. Create all tasks

## Task Status

| Status | Meaning |
|--------|---------|
| **Pending** | Not yet started |
| **In Progress** | Being worked |
| **Complete** | Finished |
| **Verified** | Completion verified |
| **Blocked** | Cannot proceed |
| **Cancelled** | No longer needed |

## Working on Tasks

### Viewing Your Tasks

1. Navigate to **Inbox** or **My Tasks**
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

## My Tasks View

The **Inbox** or **My Tasks** page shows:

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
| `view_capatask` | View tasks |
| `add_capatask` | Create tasks |
| `change_capatask` | Edit, complete tasks |
| `delete_capatask` | Remove tasks |

## Best Practices

1. **Clear titles** - Action-oriented, specific
2. **Realistic due dates** - Achievable
3. **Single owner** - One person responsible
4. **Evidence always** - Document completion
5. **Update promptly** - Keep status current

## Next Steps

- [Verification & Closure](verification.md) - Completing the CAPA
- [Creating a CAPA](creating.md) - Initial setup
- [CAPA Overview](overview.md) - Process reference
