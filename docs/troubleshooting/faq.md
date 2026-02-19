# Frequently Asked Questions

Common questions about using Ambac Tracker.

## General

### What browsers are supported?
Chrome, Firefox, Edge, and Safari (latest versions). Chrome is recommended for best performance.

### Can I use Ambac Tracker on mobile?
Yes, the interface is responsive and works on tablets and phones. For complex tasks, desktop is recommended.

### How do I change my password?
Go to **Profile** > **Change Password**. If using SSO, manage password through your identity provider.

### Can I change my email address?
Contact your administrator to change your email. It's used as your login identifier.

### How do I switch between organizations?
Click the organization name in the sidebar header and select from the dropdown (if you belong to multiple).

## Orders & Parts

### How do I find an order?
Use the **Search** bar with order number, or browse **Tracker**. Apply filters to narrow results.

### How do I add parts to an existing order?
Open the order, go to **Parts** section, click **+ Add Parts**.

### Why can't I move parts forward?
Check for: required measurements not recorded, pending approvals, FPI requirements, or hold points.

### What happens when I delete a part?
Parts are soft-deleted (archived). They're hidden from active views but retained for audit compliance.

### How do I view part history?
Open the part detail and click **History** tab. Shows all transitions, measurements, and events.

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
Navigate to **Documents**, click **+ Upload**, select file, enter metadata, and save.

### Why is my document stuck in "Draft"?
Controlled document types require approval. Click **Submit for Approval** to start the workflow.

### How do I create a new revision?
Open the document, click **New Revision**, upload new file, and submit for approval.

### Who can see my documents?
Visibility depends on document settings (Public, Internal, Confidential) and user permissions.

## Administration

### How do I add a new user?
Navigate to **Data Management** > **Users**, click **+ New User**, fill in details.

### How do I reset someone's password?
If using SSO, this is handled by your identity provider. Otherwise, use "Password Reset" function.

### How do I change user permissions?
Edit the user, modify group membership. Groups determine permissions.

### How do I create a new process?
Navigate to **Data Management** > **Processes**, click **+ New Process**, add steps, configure.

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
Yes, automatic backups occur regularly. Contact support for retention policy details.

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
Note the exact message, what you were doing, and contact support.

### Changes aren't saving
Check internet connection, refresh page, ensure you clicked Save.

### Export isn't working
Large exports take time. Check email for download link if it's big.

## Getting Help

### How do I contact support?
See [Getting Help](help.md) for support contact information.

### How do I report a bug?
Contact support with: steps to reproduce, expected vs actual behavior, screenshots.

### How do I request a feature?
Contact your account manager or submit through support channel.
