# Approval Templates

Configure approval workflows for documents, processes, and other records.

## What are Approval Templates?

See [Approvals](../../workflows/approvals/overview.md) for how requests are
raised, routed, and closed.

Approval Templates define:
- **Who** needs to approve
- **How many** approvals required
- **Order** of approvals
- **Rules** for routing

## Creating Approval Templates

1. Navigate to **Admin** > **Data Management** > **Approval Templates**
2. Click **New Approval Templates**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Template Name** *(required)* | Template name |
| **Approval Type** *(required)* | What this template approves, e.g. Document Release, CAPA Approval |
| **Approval Flow** | **All Required**, **Threshold**, or **Any** |
| **Sequence** | **Parallel** or **Sequential** |
| **Threshold (if applicable)** | How many approvals are needed when the flow is Threshold |
| **Delegation** | **Optional** or **Disabled** |
| **Auto-assign to Group** | Assign everyone in a group when a request is raised |
| **Allow Self-Approval** | Whether a requester may approve their own request |
| **Due Days** | Days until the request is due |
| **Escalation Days** | Days before it escalates |
| **Escalation Target** | Who it escalates to |

Add approvers with **Add Person** and **Add Role**, then click **Create
Template**.

## Approval Steps

Each step defines required approvals:

| Field | Description |
|-------|-------------|
!!! note "Templates have no named steps"
    A template does not contain a list of steps with their own names and
    approver sets. It has **one** set of approvers, plus a flow and a sequence
    that decide how their responses are counted.

    To model "Engineering review, then QA release", use **Sequential** with the
    approvers in order, or use two approval types.

### Approver Selection

| Option | Description |
|--------|-------------|
| **Add Person** | Named individuals |
| **Add Role** | Anyone holding that role |
| **Auto-assign to Group** | Every member of the group, assigned automatically |

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

!!! note "No mixed flow"
    A template is either Parallel or Sequential — the two cannot be combined
    within one template.

## How responses are counted

**Sequence** decides the order approvers are asked. **Approval Flow** decides
how many responses close the request:

| Flow | Closes when |
|------|-------------|
| **All Required** | Every assigned approver has approved |
| **Threshold** | The configured number of approvals is reached |
| **Any** | Any one approver approves |

These are independent: a Threshold flow can run Sequential or Parallel.

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

## The types the system looks up by name

Some workflows fetch a template **by its approval type** and refuse to proceed
without it. These are not optional configuration — if the template is missing,
the action fails with a message naming the type:

| Approval type | Requested when | Default approver |
|---------------|----------------|------------------|
| `DOCUMENT_RELEASE` | A document is routed for release | QA Manager |
| `PROCESS_APPROVAL` | A process is submitted for approval | QA Manager |
| `PCR_APPROVAL` | A process change request is submitted | QA Manager |
| `PCO_APPROVAL` | A process change order is submitted | Production Manager |
| `PCN_RELEASE` | A process change notice is released | Document Controller |
| `CAPA_APPROVAL` / `CAPA_MAJOR` / `CAPA_CRITICAL` | A CAPA needs management approval | QA Manager / Tenant Admin |
| `TRAINING_CERT` | Reserved for certifying training | QA Manager |

!!! warning "A missing template stops the workflow"
    Submitting a process change request without a `PCR_APPROVAL` template
    returns *"PCR_APPROVAL approval template not found. Please configure
    approval templates."* The three change-control types are the ones most often
    absent on an older tenant.

!!! danger "Group names must match exactly"
    **Auto-assign to group** and the default-group list are matched against the
    group name character for character. `QA_Manager` does **not** match the group
    **QA Manager** — and a name that matches nothing assigns **nobody**,
    silently, because a search that finds no one is not an error.

    The real names have spaces and no underscores: **QA Manager**, **Production
    Manager**, **Document Controller**, **Tenant Admin**, **Shift Lead**,
    **QA Inspector**, **Operator**. See [Roles](../users/roles.md).

!!! note "There is no ECO template"
    Engineering change orders originate in your PLM, not here. Nothing in uqmes
    requests an `ECO` approval. Process change is `PCR` → `PCO` → `PCN`.

## Template Examples

These are illustrative shapes, not shipped templates.

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
```

### Process Change
```
Template: PCR Approval
Step 1: Quality (1 of 1)      - QA Manager
Step 2: Production (1 of 1)   - Production Manager
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

