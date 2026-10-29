# Approval Templates

Configure approval workflows for documents, processes, and other records.

## What are Approval Templates?

See [Approvals](../../workflows/approvals/overview.md) for how requests are
raised, routed, and closed.

Approval Templates define:

- **Who** needs to approve
- **How many** approvals required
- **Sequence** — everyone at once, or one at a time

!!! important "One current template per approval type"
    An organisation has **one** current template for each approval type — a
    second template of the same type is refused. To change how a type is
    approved, edit its template: saving creates a new version, and requests
    raised after that use it. A request already open keeps the approvers it was
    created with.

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

Add approvers — with **Add Person** and **Add Role** for a **Parallel**
template, or in **stages** for a **Sequential** one (see [Sequence](#sequence))
— then click **Create Template**.

## Who approves

A **Parallel** template has one set of approvers, all asked at once. A
**Sequential** template has numbered **stages** — *Stage 1*, *Stage 2* … — each
with its own people and groups, answered in turn. Stages are numbered, not
named.

### Approver Selection

| Option | Description |
|--------|-------------|
| **Add Person** | A named individual, assigned to every request as a **required** approver |
| **Add Role** | A group whose members may each respond. The group itself is not a required approver |
| **Auto-assign to Group** | Every member of the named group, assigned to each request as a **required** approver |

!!! warning "On a Parallel template, a role added with Add Role is not required"
    **Add Role** makes a group's members *eligible* to respond; on a **Parallel**
    template it does not make anyone *required*. Only named people (**Add
    Person**) and the members brought in by **Auto-assign to Group** count as
    required approvers — so under **All Required**, a Parallel template whose
    approvers are roles only closes on the first approval from any member.

    To require every member of a group, name it in **Auto-assign to Group**. To
    require one specific person, add them with **Add Person**. On a
    **Sequential** template a group *is* required — see below.

## Sequence

**Parallel** asks everyone at once. **Sequential** runs in **stages**, each
answering only after the one before is done.

Setting **Sequence** to **Sequential** replaces the approvers list with stage
cards. Each stage takes people and groups; **Move up**, **Move down** and
**Remove** reorder and drop stages, and **Add stage** adds one. As the form
says: *"Each stage answers in turn — a later stage can't approve or reject
until every earlier one is done. Everyone named in a stage must approve; for a
group, any one member. The auto-assign group, if set, is a final stage after
these."*

The order is enforced, not just suggested:

- **Only the open stage can answer.** Anyone in a later stage who tries to
  approve or reject is refused — *"Not your turn — waiting on &lt;names or
  groups&gt;."* Only the open stage is notified; the next stage is notified when
  it opens.
- **A stage is done** when everyone named in it has approved and each of its
  groups has been answered by one member. A group in a stage is **required**.
- **A rejection at any stage ends the request.** Later stages are never asked;
  starting again means a new request, from stage 1.
- **A response can be withdrawn only while its stage is still open.** Once a
  later stage has answered, it is refused — *"A later stage has already
  answered, so this response stands."*
- **Each request keeps the stages it was created with.** Editing the template
  changes only requests raised afterwards.
- A delegated approval keeps its place in the order.

!!! note "No mixed flow"
    A template is either Parallel or Sequential — the two cannot be combined
    within one template.

## How responses are counted

**Sequence** decides the order approvers are asked. **Approval Flow** decides
how many responses close the request:

| Flow | Closes when |
|------|-------------|
| **All Required** | Every required approver has approved |
| **Threshold** | The configured number of approvals is reached |
| **Any** | Any one approver approves |

Under **Sequential**, the request closes when every stage is done, as described
above. The flow matters only for the **Auto-assign to Group** stage at the end:
under **All Required** every member of that group must approve; otherwise any
one member answers for it. **Threshold** and **Any** otherwise apply to
**Parallel** requests, and count approvals from anyone eligible — named people,
auto-assigned members, and members of a role added with **Add Role**.

## The types the system looks up by name

Some workflows fetch the template **by its approval type** and refuse to
proceed without it — the action fails with a message naming the type:

| Approval type | Requested when | Starter template assigns |
|---------------|----------------|--------------------------|
| `DOCUMENT_RELEASE` | A document is routed for release and its document type has no approval template of its own | QA Manager |
| `PROCESS_APPROVAL` | A process is submitted for approval | QA Manager |
| `PCR_APPROVAL` | A process change request is submitted | QA Manager |
| `PCO_APPROVAL` | A process change order is submitted for its own approval (Regulated change control) | Production Manager |

!!! warning "A missing template stops the workflow"
    Submitting a process change request without a `PCR_APPROVAL` template
    returns *"PCR_APPROVAL approval template not found. Please configure
    approval templates."* The other three refuse with the same message naming
    their own type.

The CAPA types are looked up too, but a missing one does not stop a CAPA being
created — see [Severity chooses the CAPA template](#capa-authorisation) below:

| Approval type | Requested when | Starter template assigns |
|---------------|----------------|--------------------------|
| `CAPA_CRITICAL` | A **Critical** CAPA is created, or its approval requested | QA Manager |
| `CAPA_MAJOR` | A **Major** CAPA is created, or its approval requested | QA Manager |
| `CAPA_APPROVAL` | Any other CAPA approval request, and the fallback when the two above are missing | QA Manager |

Two more types have starter templates that nothing uses:

- `PCN_RELEASE` — releasing a process change notice raises no approval; the
  template is never looked up.
- `TRAINING_CERT` — nothing raises a training certification approval.

!!! danger "Auto-assign to Group stores the group's name"
    **Auto-assign to Group** keeps the group's **name**, and each new request
    matches it against group names character for character. If that group is
    later renamed, the template matches nobody and assigns **nobody** —
    silently, because a search that finds no one is not an error. Pick the group
    again after renaming one. (Roles added with **Add Role** are held by
    reference and follow a rename.)

    The real names have spaces and no underscores: **QA Manager**, **Production
    Manager**, **Document Controller**, **Tenant Admin**, **Shift Lead**,
    **QA Inspector**, **Operator**. See [Roles](../users/roles.md).

!!! note "There is no ECO template"
    Engineering change orders originate in your PLM, not here. Nothing in uqmes
    requests an `ECO` approval. Process change is `PCR` → `PCO` → `PCN`.

## Template Examples

These are illustrative shapes, not shipped templates.

### Document approval

Sequence **Sequential**: stage 1 the engineering lead (a person), stage 2 the
**QA Manager** group, stage 3 the production manager (a person). The engineering
lead answers first; then any one QA Manager; then the production manager. Until
stage 1 has approved, a QA Manager trying to approve is told *"Not your turn —
waiting on &lt;engineering lead&gt;."*

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

Sequence **Parallel**, flow **All Required**, with the QA manager and the
production manager each added with **Add Person** — both asked at once, and the
request closes when both have approved. Adding the **QA Manager** and
**Production Manager** roles with **Add Role** instead would close it on the
first approval from either group, because a role is never a required approver.

!!! tip "Use Threshold when any two of several will do"
    For "any 2 of 3 engineers", set flow **Threshold** with Threshold 2 and add
    all three as approvers.

## Applying Templates

Templates are matched by **approval type**, not chosen at the moment of
submitting. There are three places the binding is made:

### By approval type (the default)

Each type resolves to its current template. Nothing to configure beyond having
the template exist — this is how PCRs, PCOs, CAPAs and the rest find theirs.

### Per document type (the override)

1. Edit the **document type** (see [Document Types](document-types.md))
2. With **Requires Approval** ticked, pick its **Approval template**
3. Every document of that type routes through it instead of Document Release

Left on its first option, *The default document approval*, the type uses the
current `DOCUMENT_RELEASE` template. This is how two kinds of document can route
to different approvers.

!!! note "A submitter never picks a template"
    There is no template selector on the submit dialog and no per-document
    override. Someone routing a document for release chooses nothing — the type
    decides. If the wrong people are being asked, the fix is on the document
    type or the template, not on the document.

### Per sampling rule set (a quality gate)

A sampling rule set whose gate includes **Require approval** names its own
**Approval template**. When the gate trips, the approval is raised from that
template, whatever its approval type. See [Gates: reacting to bad
results](sampling-rules.md#gates-reacting-to-bad-results).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_approvaltemplate` | View templates |
| `add_approvaltemplate` | Create templates |
| `change_approvaltemplate` | Edit templates |
| `delete_approvaltemplate` | Remove templates |

