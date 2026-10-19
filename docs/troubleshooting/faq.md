# Frequently Asked Questions

Common questions about using uqmes.

!!! tip "Worked examples, on the demo dataset"
    These examples use record numbers from the **demo dataset**, which exists
    only if your system was seeded with it. On your own data the questions still
    apply; the identifiers will not. See
    [Training Data Setup](../training/training-data-setup.md) for how to load it.

    - **Find an order**: `ORD-2024-0042` (Midwest Fleet, 24 injectors)
    - **View part history**: INJ-0042-017 — a Flow Testing failure and its disposition
    - **Create a CAPA**: CAPA-2024-003, a complete nozzle defect investigation
    - **Explore permissions**: sign in as different demo users to see how
      role-based access changes what you can reach

    Demo accounts — all with the password **`demo123`**:
    `mike.ops@demo.ambac.com` (Operator), `sarah.qa@demo.ambac.com` (QA
    Inspector), `jennifer.mgr@demo.ambac.com` (Production Manager).

## General

### What browsers are supported?
Chrome, Firefox, Edge, and Safari (latest versions). Chrome is recommended for best performance.

### Can I use uqmes on mobile?
Yes, the interface is responsive and works on tablets and phones. For complex tasks, desktop is recommended.

### How do I change my password?
Open the user menu at the bottom of the sidebar, choose **Profile**, and use the **Change Password** card there. If you sign in with SSO, your password is managed by your identity provider, not here.

### Can I change my email address?
Contact your administrator. Your **username** is your login identifier, not
your email, so changing one does not change the other.

### How do I switch between organizations?
Click the organization name at the **top of the sidebar** and select from the
menu (if you belong to multiple).

## Orders & Parts

### How do I find an order?
There is **no application-wide search bar**. Open the list page for what you
want — **Tracker** for orders, or **Data Management** > **Orders** — and use
that page's own search and filters.

### How do I add parts to an existing order?
Not from the order page, which is read-only. Parts are added against the **work
order**: **Production** > **WO Control Center**, tick exactly one work order,
then **Add Parts** in the bulk bar. See
[Adding Parts](../workflows/orders/adding-parts.md).

### Why can't I move parts forward?
You don't move parts — they advance on their own once the step's requirements
are met. The most common reason one appears stuck is **lot cohesion**: parts
that haven't been split advance together, so an unfinished part elsewhere in the
lot holds yours. Also check for a pending First Piece Inspection, missing
captures, quarantine, or a training gap. See
[Common Issues](common-issues.md#parts-stuck-at-step).

### What happens when I delete a part?
Parts are soft-deleted (archived). They're hidden from active views but retained for audit compliance.

### How do I view part history?
Open the part detail. The **Activity History** section on that page shows the audit trail; quality reports and dispositions have their own sections. See [Part History](../workflows/tracking/part-history.md).

## Quality

### How do I create a quality report (NCR)?
Select affected part(s), click **Create Quality Report**, fill in details, and submit.

### What's the difference between Minor, Major, and Critical?
- **Minor**: Cosmetic, no functional impact
- **Major**: Out of spec, affects function
- **Critical**: Safety or regulatory concern

### When should I create a CAPA?
For recurring issues, major/critical NCRs, customer complaints, or audit findings.

### How do I close a CAPA?
Complete all tasks, document verification, then click **Request Closure**. Approver must approve.

## Documents

### How do I upload a document?
Navigate to **Documents**, click **Upload Document**, select file, enter metadata, and save.

### Why is my document stuck in "Draft"?
Controlled document types require approval. Click **Submit for Approval** to start the workflow.

### How do I create a new revision?
Open the document, click **Create Revision**, upload new file, and submit for approval.

### Who can see my documents?
Visibility depends on the document's classification — **Public, Internal,
Confidential, Restricted** or **Secret** — and on your permissions. Note that
Confidential and Restricted are by default held by every staff role: **Secret** is the only
tier that keeps a document from most of the shop. See [Classification
Levels](../workflows/documents/library.md#classification-levels).

## Administration

### How do I add a new user?
Navigate to **Admin** > **User Management**, click **Add user**, fill in the details, then **Create User**.

### How do I reset someone's password?
If using SSO, this is handled by your identity provider. Otherwise, use "Password Reset" function.

### How do I change user permissions?
Edit the user, modify group membership. Groups determine permissions.

### How do I create a new process?
Navigate to **Production** > **Processes**, click **New Process**, add steps, configure.

## Technical

### What's the difference between Order and Work Order?
**Order**: Customer request (what they ordered)
**Work Order**: Production assignment (how we make it)

### What's the difference between FPI and FAI?
**FPI (First Piece Inspection)**: Setup verification, done each run
**FAI (First Article Inspection)**: Full qualification, done once

### What does "archived" mean?
Soft-deleted. Record is hidden from active views but retained for compliance.

### Why do I see different data than my colleague?
Check: same tenant selected, same filters applied, permission differences.

## Compliance

### Is my data backed up?
**That depends on your deployment, and it is not configured in uqmes.** Backup
schedule and retention are properties of the database and hosting your
organisation runs — there is no backup setting in the application. Ask whoever
operates it what the policy is; do not assume one exists.

### How long are records kept?
Per your organization's retention policy, typically 7+ years for quality records.

### Can audit logs be modified?
No. PostgreSQL triggers reject UPDATE and DELETE on the audit tables, and they
apply to superusers too — so this holds even for someone connecting directly
to the database, not just through the application.

Where pgAudit is present it additionally logs write, DDL and role statements,
so an attempt to remove a trigger would itself be recorded — **but it is not
part of every deployment.** It comes from the custom Postgres image, so a
managed or templated database may not have it, while the triggers travel with
every deployment. Confirm which layers you actually have before describing them
to an assessor. See [Audit
Trails](../compliance/audit-trails.md#immutability).

### How do I export data for an audit?
It depends what you need.

**Audit log data cannot be exported from the UI** — export is deliberately
disabled on the audit log viewer. Filter it on screen to confirm the scope, then
pull the same range from `GET /api/auditlog/` with the same filter parameters.
That needs `export_auditlog`. See
[Audit Trails](../compliance/audit-trails.md).

**Other data** — wherever a list's toolbar offers **Export**, it exports CSV or
Excel. If a list has no Export button, that model cannot be exported; it is not
a permissions problem. PDF is not an export format for list data.

## Troubleshooting

### The page won't load
Try: refresh, clear cache, different browser, check internet connection.

### I'm seeing an error message
Note the exact message and what you were doing, then check [Common Issues](common-issues.md) — the docs quote real error text, so searching the words on screen often lands on the answer.

### Changes aren't saving
Check internet connection, refresh page, ensure you clicked Save.

### Export isn't working
Exports download directly in the browser rather than arriving by email. A
large one holds the request open while it builds, so leave the tab open and
narrow the filters or date range if it times out.

## Getting Help

### Who do I contact when something is broken?
Whoever administers uqmes for your organization — nothing in the system raises a
request for you. See [Getting Help](help.md) for what to try first and what to
include.

### How do I report a bug?
Raise it with whoever maintains the deployment, with: steps to reproduce, expected vs actual behaviour, and the exact error text. See [Writing a report worth reading](help.md#writing-a-report-worth-reading).

### How do I request a feature?
Raise it with whoever maintains uqmes for your organization. There is no
vendor intake process.
