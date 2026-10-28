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

## Who approves

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

## Sequence

**Sequential** asks the approvers one at a time, in order — each is approached
only once the one before has responded. **Parallel** asks all of them at once.

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

Under **Sequential**, the flow is not used: the request closes only when every
required approver has approved, in turn. **Threshold** and **Any** apply to
**Parallel** requests.

!!! warning "Some older field names were never real"
    An earlier version of this page described a **Required Count** field, a
    **Backup Approvers** list, and an **Auto-Approval** setting. None of them
    exists. The nearest real fields are:

    - **Threshold** — the count for a Threshold flow (not "Required Count")
    - **Escalation Target** — who it goes to after **Escalation Days** (not a
      backup approver list)
    - **Allow Self-Approval** — whether a requester may approve their own
      request, which is not auto-approval

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
| `CAPA_CRITICAL` | A **Critical** CAPA is created, or its approval requested | QA Manager |
| `CAPA_MAJOR` | A **Major** CAPA is created, or its approval requested | QA Manager |
| `CAPA_APPROVAL` | Any other CAPA approval request, and the fallback when the two above are missing | QA Manager |
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

These are illustrative shapes, not shipped templates. Each is **one** template
with one set of approvers — there are no named steps to list.

### Document approval

Sequence **Sequential**, flow **All Required**, approvers in order: the document
owner, the Engineering role, then QA Manager. Each is asked once the one before
has responded.

### CAPA authorisation

Sequence **Parallel**, flow **Any**, approver group QA Manager — the first
approval decides it. The starter **Critical CAPA Approval** and **Major CAPA
Approval** templates have this shape: a Major or Critical CAPA's plan is approved
by a QA Manager only. A request already open keeps the approvers it was created
with; editing a template changes only the requests raised after it.

!!! note "Severity chooses the CAPA template"
    A **Critical** CAPA raises its approval from a `CAPA_CRITICAL` template and
    a **Major** one from `CAPA_MAJOR` — both when the CAPA is created and when
    approval is requested by hand. Where the organisation has no template of
    that type, the general `CAPA_APPROVAL` is used instead.

    With **no** CAPA template at all, a Critical or Major CAPA is created
    without an approval request; that is treated as a deliberate choice, and
    only the server log records it. Requesting approval by hand is then refused
    — *"No CAPA approval template is configured. Add one in approval
    templates."*

!!! warning "There is no CAPA *closure* approval to configure"
    A Major or Critical CAPA raises its approval **at creation** — authorisation
    for the work to begin. **Closure is not an approval at all**: it follows
    from recording an *Effective - Confirmed* verification, gated by `verify_capa`.

    So do not build a template expecting to gate closure with it. Approving a
    CAPA and verifying one are different acts by potentially different people,
    and only the first is routable here.

### Process change

Sequence **Parallel**, flow **All Required**, approvers QA Manager and
Production Manager — both asked at once, and the request closes when both have
approved.

!!! tip "Use Threshold when any two of several will do"
    For "any 2 of 3 engineers", set flow **Threshold** with Threshold 2 and add
    all three as approvers.

## Applying Templates

Templates are matched by **approval type**, not chosen at the moment of
submitting. There are two places the binding is made:

### By approval type (the default)

Each type resolves to its current template. Nothing to configure beyond having
the template exist — this is how PCRs, PCOs, CAPAs and the rest find theirs.

### Per document type (the override)

1. Edit the **document type**
2. Set its **approval template**
3. Every document of that type routes through it instead of Document Release

Leave it blank and the type uses **Document Release**. This is how two kinds of
document can route to different approvers.

!!! note "A submitter never picks a template"
    There is no template selector on the submit dialog and no per-document
    override. Someone routing a document for release chooses nothing — the type
    decides. If the wrong people are being asked, the fix is on the document
    type or the template, not on the document.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_approvaltemplate` | View templates |
| `add_approvaltemplate` | Create templates |
| `change_approvaltemplate` | Edit templates |
| `delete_approvaltemplate` | Remove templates |

