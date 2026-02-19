# Approval Templates

Configure approval workflows for documents, processes, and other records.

## What are Approval Templates?

Approval Templates define:
- **Who** needs to approve
- **How many** approvals required
- **Order** of approvals
- **Rules** for routing

## Creating Approval Templates

1. Navigate to **Data Management** > **Approval Templates**
2. Click **+ New Template**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Name** | Template name |
| **Description** | When to use |
| **Applies To** | Documents, Processes, CAPAs |

4. Add approval steps
5. Save

## Approval Steps

Each step defines required approvals:

| Field | Description |
|-------|-------------|
| **Name** | Step name (e.g., "Engineering Review") |
| **Approvers** | Who can approve |
| **Required Count** | How many must approve |
| **Order** | Sequential or parallel |

### Approver Selection

| Option | Description |
|--------|-------------|
| **Specific Users** | Named individuals |
| **Group Members** | Anyone in a group |
| **Role** | Anyone with specific role |

## Approval Flow Types

### Sequential
Approvals happen in order:
```
Step 1: Engineering → Step 2: QA → Step 3: Management
```
Each must complete before next starts.

### Parallel
All approve simultaneously:
```
Step 1: Engineering + QA + Management (all at once)
```
Complete when all approve.

### Mixed
Combination:
```
Step 1: Engineering (sequential first)
Step 2: QA + Production (parallel)
Step 3: Final approval (sequential last)
```

## Approval Rules

### Threshold Approvals
"2 of 3 must approve":
1. Set **Required Count** to 2
2. Add 3 possible approvers
3. Any 2 approving completes step

### Backup Approvers
If primary unavailable:
1. Add backup approvers to step
2. Escalation after X days
3. Backup can approve

### Auto-Approval
For specific conditions:
- Low-risk changes
- Same approver as previous
- Within thresholds

## Template Examples

### Document Approval
```
Template: Engineering Document
Step 1: Author Review (1 of 1) - Document owner
Step 2: Technical Review (1 of 2) - Engineering group
Step 3: QA Approval (1 of 1) - QA Manager
```

### CAPA Closure
```
Template: CAPA Closure
Step 1: Verification Complete (1 of 1) - QA Inspector
Step 2: Effectiveness Confirmed (1 of 1) - QA Manager
Step 3: Final Approval (1 of 1) - Quality Director
```

### Process Change
```
Template: Process Change
Step 1: Engineering (1 of 1)
Step 2: Quality (1 of 1)
Step 3: Operations (1 of 1)
Step 4: Management (for major changes)
```

## Applying Templates

### Default for Document Type
1. Edit document type
2. Set default approval template
3. All documents of type use this template

### Per Document
1. When submitting for approval
2. Select template
3. Override default if needed

## Permissions

| Permission | Allows |
|------------|--------|
| `view_approvaltemplate` | View templates |
| `add_approvaltemplate` | Create templates |
| `change_approvaltemplate` | Edit templates |
| `delete_approvaltemplate` | Remove templates |

## Best Practices

1. **Match to risk** - More approvals for critical items
2. **Include backups** - Handle absences
3. **Clear naming** - Describe purpose
4. **Test thoroughly** - Verify flow works
5. **Review periodically** - Adjust as org changes
