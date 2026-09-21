# Frequently Asked Questions

Common questions about using uqmes.

!!! tip "Try It in Demo Mode"
    These FAQs reference real demo data you can explore:

    - **Find an order**: Search for `ORD-2024-0042` (Midwest Fleet, 24 injectors)
    - **View part history**: Open INJ-0042-017 to see Flow Testing failure and disposition
    - **Create a CAPA**: See CAPA-2024-003 for a complete nozzle defect investigation
    - **Explore permissions**: Log in as different demo users to see RBAC in action

    Demo accounts: mike.ops@demo.ambac.com (Operator), sarah.qa@demo.ambac.com (QA Inspector), jennifer.mgr@demo.ambac.com (Production Manager)

## General

### What browsers are supported?
Chrome, Firefox, Edge, and Safari (latest versions). Chrome is recommended for best performance.

### Can I use uqmes on mobile?
Yes, the interface is responsive and works on tablets and phones. For complex tasks, desktop is recommended.

### How do I change my password?
Open the user menu at the bottom of the sidebar, choose **Profile**, and use the **Change Password** card there. If you sign in with SSO, your password is managed by your identity provider, not here.

### Can I change my email address?
Contact your administrator to change your email. It's used as your login identifier.

### How do I switch between organizations?
Click the organization name at the **top of the sidebar** and select from the
menu (if you belong to multiple).

## Orders & Parts

### How do I find an order?
Use the **Search** bar with order number, or browse **Tracker**. Apply filters to narrow results.

### How do I add parts to an existing order?
Open the order, go to **Parts** section, click **Add Parts**.

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
Visibility depends on document settings (Public, Internal, Confidential) and user permissions.

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
Yes. Your administrator configures the schedule and how long backups are kept.

### How long are records kept?
Per your organization's retention policy, typically 7+ years for quality records.

### Can audit logs be modified?
No. Audit logs are immutable and protected at the database level.

### How do I export data for an audit?
Navigate to relevant section, apply filters, click **Export**. Choose PDF or CSV.

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
There is no support desk. See [Getting Help](help.md) for what to try and who
to raise it with.

### How do I report a bug?
Raise it with whoever maintains the deployment, with: steps to reproduce, expected vs actual behaviour, and the exact error text. See [Writing a report worth reading](help.md#writing-a-report-worth-reading).

### How do I request a feature?
Raise it with whoever maintains uqmes for your organization. There is no
vendor intake process.
