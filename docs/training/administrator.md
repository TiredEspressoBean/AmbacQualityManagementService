# Administrator Training Guide

**Duration:** 6-8 hours
**Prerequisites:** Understanding of all user roles
**Goal:** Learn to configure the system, manage users, set up processes, and maintain system health

---

## Module 1: Administrator Role Overview

### Learning Objectives

By the end of this module, you will:

- [ ] Understand administrator responsibilities
- [ ] Navigate administration screens
- [ ] Understand the impact of configuration changes

### 1.1 Your Role

As an Administrator, you:

- Manage user accounts and permissions
- Configure processes and workflows
- Set up system master data
- Maintain integrations
- Monitor system health
- Support users with access issues

Your configuration decisions affect all users.

---

### 1.2 Administration Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Data Management** | Admin > Data Management | All editors |
| **Users** | Data Management > Users | User accounts |
| **Groups** | Data Management > Groups | Permission groups |
| **Settings** | Admin > Settings | System configuration |
| **Audit Log** | Admin > Audit Log | Activity monitoring |

**Exercise 1.1:** Navigate Admin Pages

1. Visit each administration page
2. Note available options on each
3. Identify what can be configured

---

### 1.3 Configuration Impact

!!! warning "Changes Affect Everyone"
    Configuration changes take effect immediately and affect all users. Test in training environment first when possible.

---

### Knowledge Check: Module 1

1. What are the main responsibilities of an administrator?
2. Where do you manage user accounts?
3. Why is it important to understand the impact of configuration changes?

---

## Module 2: User Management

### Learning Objectives

By the end of this module, you will:

- [ ] Create user accounts
- [ ] Assign users to groups
- [ ] Deactivate users properly

### 2.1 User Account Fields

| Field | Description | Required |
|-------|-------------|----------|
| **Email** | Login ID, must be unique | Yes |
| **First Name** | Display name | Yes |
| **Last Name** | Display name | Yes |
| **Role Type** | Staff, Customer, Auditor | Yes |
| **Groups** | Permission groups | Yes |
| **Active** | Can login if checked | Yes |

---

### 2.2 Creating a User

**Steps:**

1. Navigate to **Data Management** > **Users**
2. Click **+ New User**
3. Fill in:
   - Email address (will be login)
   - First and last name
   - Role type (Staff for internal, Customer for external)
   - Assign to appropriate groups
4. Save

**What happens:**

- User account created
- Invitation email sent
- User sets password via link

**Exercise 2.1:** Create a User

1. Go to Users
2. Create new user:
   - Email: trainee1@example.com
   - First Name: Training
   - Last Name: User One
   - Role Type: Staff
   - Groups: Add to "Operators" group
3. Save

---

### 2.3 Role Types

| Role Type | Purpose | Access |
|-----------|---------|--------|
| **Staff** | Internal employees | Full internal access |
| **Customer** | External customers | Read-only, their data only |
| **Auditor** | External auditors | Read-only, audit access |

Choose carefully - this limits available permissions.

---

### 2.4 Deactivating Users

**When employees leave:**

1. Open user record
2. Uncheck **Active**
3. Save

**What happens:**

- User cannot log in
- History and audit trail preserved
- Account can be reactivated if needed

**Don't delete users** - always deactivate to preserve history.

---

### 2.5 Password Resets

**If user forgets password:**

1. Direct them to "Forgot Password" on login
2. Or: Open user record → **Reset Password**
3. User receives reset email

**With SSO:** Password is managed by identity provider, not in Ambac Tracker.

---

### Knowledge Check: Module 2

1. What's the difference between Staff and Customer role types?
2. Why do you deactivate instead of delete users?
3. How does a user set their initial password?

---

## Module 3: Groups and Permissions

### Learning Objectives

By the end of this module, you will:

- [ ] Create permission groups
- [ ] Assign permissions to groups
- [ ] Follow principle of least privilege

### 3.1 Permission Model

```
Users → Groups → Permissions
```

- Users belong to one or more groups
- Groups have permissions assigned
- User gets all permissions from all their groups

---

### 3.2 Creating Groups

**Steps:**

1. Navigate to **Data Management** > **Groups**
2. Click **+ New Group**
3. Name the group (e.g., "Operators", "QA Inspectors")
4. Add description
5. Save
6. Assign permissions

**Exercise 3.1:** Create a Group

1. Go to Groups
2. Create new:
   - Name: "Training Operators"
   - Description: "Operators in training, limited access"
3. Save

---

### 3.3 Assigning Permissions

**On group detail page:**

1. Go to **Permissions** section
2. Browse available permissions
3. Check permissions to grant
4. Save

**Permission categories:**

| Category | Examples |
|----------|----------|
| **View** | Can see data |
| **Add** | Can create records |
| **Change** | Can edit records |
| **Delete** | Can remove records |

**Exercise 3.2:** Assign Permissions

1. Open "Training Operators" group
2. Add permissions:
   - View orders (yes)
   - View parts (yes)
   - Pass parts (yes)
   - Create orders (no)
3. Save

---

### 3.4 Principle of Least Privilege

**Best practice:** Give users only the permissions they need.

**Why:**

- Reduces risk of mistakes
- Limits security exposure
- Easier to audit
- Compliance requirement

---

### 3.5 Common Group Templates

| Group | Typical Permissions |
|-------|---------------------|
| **Operators** | View orders, pass parts, flag issues |
| **QA Inspectors** | Above + quality reports, inspections |
| **QA Managers** | Above + approve dispositions, manage CAPAs |
| **Production Managers** | Create orders, work orders, view all |
| **Document Controllers** | Manage documents, revisions |
| **Administrators** | Full system access |

---

### Knowledge Check: Module 3

1. How do users get permissions?
2. What is the principle of least privilege?
3. Why assign permissions to groups rather than users?

---

## Module 4: Process Configuration

### Learning Objectives

By the end of this module, you will:

- [ ] Create manufacturing processes
- [ ] Configure process steps
- [ ] Set up measurement requirements

### 4.1 Process Structure

```
Process → Steps → Requirements (Measurements, Documents, Training)
```

Processes define how parts move through production.

---

### 4.2 Creating a Process

**Steps:**

1. Navigate to **Data Management** > **Processes**
2. Click **+ New Process**
3. Fill in:
   - Name: Descriptive name
   - Description: What this process is for
   - Version: Start at 1.0
4. Save (draft created)
5. Add steps

**Exercise 4.1:** Create a Process

1. Go to Processes
2. Create new:
   - Name: "Training Widget Assembly"
   - Description: "Assembly process for training widgets"
3. Save

---

### 4.3 Adding Steps

**For each step:**

1. Click **+ Add Step**
2. Configure:
   - Name: Step name (e.g., "Machining")
   - Sequence: Order in process
   - Description: What happens here
   - Equipment type: (optional) Required equipment
3. Save
4. Add requirements

**Exercise 4.2:** Add Steps

Add these steps to your training process:

1. "Receiving" - Sequence 1
2. "Machining" - Sequence 2
3. "Finishing" - Sequence 3
4. "Final Inspection" - Sequence 4
5. "Packaging" - Sequence 5

---

### 4.4 Measurement Requirements

**For each step requiring measurements:**

1. Open step
2. Go to **Measurements** section
3. Click **+ Add Measurement**
4. Configure:
   - Name: What's measured
   - Type: Numeric, Pass/Fail, etc.
   - Target value (if applicable)
   - Tolerance (if applicable)
5. Save

**Exercise 4.3:** Add Measurements

For "Final Inspection" step:

1. Add measurement "Outer Diameter"
   - Type: Numeric
   - Target: 25.0
   - Unit: mm
   - Tolerance: ±0.05

---

### 4.5 Process Approval

**Before use, process needs approval:**

1. Review all steps and requirements
2. Click **Submit for Approval**
3. Approvers review
4. Once approved, process is released

---

### Knowledge Check: Module 4

1. What defines how parts move through production?
2. What can you configure for each step?
3. Can a process be used before it's approved?

---

## Module 5: Master Data Setup

### Learning Objectives

By the end of this module, you will:

- [ ] Set up companies (customers/suppliers)
- [ ] Configure part types
- [ ] Set up equipment and error types

### 5.1 Companies

**Creating customers/suppliers:**

1. Navigate to **Data Management** > **Companies**
2. Click **+ New Company**
3. Fill in:
   - Name
   - Type (Customer, Supplier, Both)
   - Contact information
4. Save

**Exercise 5.1:** Create a Company

Create training customer:
- Name: "Training Customer Inc."
- Type: Customer
- Industry: Manufacturing

---

### 5.2 Part Types

**Setting up products:**

1. Navigate to **Data Management** > **Part Types**
2. Click **+ New Part Type**
3. Fill in:
   - Name: Product name
   - Part Number: Your numbering
   - Default Process: Which process to use
4. Save

---

### 5.3 Equipment

**Registering equipment:**

1. Navigate to **Data Management** > **Equipment**
2. Create equipment records
3. Set equipment types
4. Configure calibration tracking if needed

---

### 5.4 Error Types

**Defining defect categories:**

1. Navigate to **Data Management** > **Error Types**
2. Create defect categories:
   - Name: Clear description
   - Severity default: Minor/Major/Critical
3. Keep categories specific but not too narrow

---

### 5.5 Document Types

**Categories for documents:**

1. Navigate to **Data Management** > **Document Types**
2. Create types:
   - Work Instruction
   - Specification
   - Drawing
   - Certificate
3. Configure approval requirements per type

---

### Knowledge Check: Module 5

1. What information is needed to create a part type?
2. Why define error types?
3. How are document types used?

---

## Module 6: System Settings

### Learning Objectives

By the end of this module, you will:

- [ ] Configure organization settings
- [ ] Set up integrations
- [ ] Manage system preferences

### 6.1 Organization Settings

**Navigate to Settings:**

- Organization name
- Timezone
- Date/number formats
- Branding (logo, colors)

---

### 6.2 Integration Settings

**Configure connections:**

- SSO/Azure AD: Single sign-on
- HubSpot: CRM integration
- API access: For integrations

**Exercise 6.1:** Review Settings

1. Go to Admin > Settings
2. Review organization settings
3. Check integration status
4. Note what can be configured

---

### 6.3 Notification Settings

**Configure:**

- Email templates
- Notification triggers
- Default preferences

---

## Module 7: Monitoring and Maintenance

### Learning Objectives

By the end of this module, you will:

- [ ] Monitor system activity
- [ ] Review audit logs
- [ ] Perform regular maintenance

### 7.1 Audit Log Review

**Navigate to Admin > Audit Log:**

- View all system activity
- Filter by user, action, date
- Export for compliance

**Look for:**

- Permission changes
- Unusual patterns
- Failed login attempts
- Configuration changes

**Exercise 7.1:** Review Audit Log

1. Go to Audit Log
2. Filter to last 7 days
3. Find permission changes
4. Export a report

---

### 7.2 System Health

**Monitor:**

- User adoption metrics
- Performance issues
- Error patterns
- Storage usage

---

### 7.3 Periodic Tasks

**Weekly:**

- [ ] Review new user requests
- [ ] Check pending access issues
- [ ] Monitor system alerts

**Monthly:**

- [ ] Permission audit
- [ ] Deactivate stale accounts
- [ ] Review group configurations
- [ ] Check integration health

**Quarterly:**

- [ ] Full permission review
- [ ] Process configuration audit
- [ ] User training needs assessment

---

## Module 8: Security and Compliance

### Learning Objectives

By the end of this module, you will:

- [ ] Follow security best practices
- [ ] Support compliance requirements
- [ ] Handle security incidents

### 8.1 Security Best Practices

- Regular permission reviews
- Prompt user deactivation when leaving
- Strong password policies (or SSO)
- Audit log monitoring
- Principle of least privilege

---

### 8.2 Compliance Support

For audits, maintain:

- Up-to-date user list
- Clear permission documentation
- Audit trails
- Training records

---

### 8.3 Incident Response

**If security issue discovered:**

1. Document the issue
2. Contain if possible (deactivate accounts)
3. Report to management
4. Investigate
5. Remediate
6. Document lessons learned

---

## Module 9: Troubleshooting

### Learning Objectives

By the end of this module, you will:

- [ ] Diagnose common user issues
- [ ] Resolve access problems
- [ ] Know when to escalate

### 9.1 User Can't Log In

**Check:**

1. Account is active
2. Password not expired (or SSO working)
3. Account not locked
4. Correct URL

---

### 9.2 Permission Issues

**When user can't do something:**

1. Check their groups
2. Verify group has permission
3. Check role type restrictions
4. Confirm tenant assignment (if multi-tenant)

**Exercise 9.1:** Troubleshoot Access

1. Find user "noaccess@example.com" (training data)
2. Identify why they can't view orders
3. Fix the issue

---

### 9.3 When to Escalate

**Contact support for:**

- Platform issues
- Integration failures
- Performance problems
- Security concerns

---

## Practical Assessment

### Task 1: User Setup

1. Create new user account
2. Assign appropriate groups
3. Verify permissions are correct

### Task 2: Group Configuration

1. Create new group for "Senior Operators"
2. Assign permissions (more than regular operators)
3. Add a user to the group

### Task 3: Process Creation

1. Create a simple 3-step process
2. Add measurement to one step
3. Submit for approval

### Task 4: Audit Review

1. Review audit log for today
2. Find all user creations
3. Export report

### Task 5: Troubleshooting

1. User "trainee-broken@example.com" can't pass parts
2. Diagnose the issue
3. Fix and verify

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Demonstrated with senior administrator

### Competencies Verified

- [ ] Can manage users correctly
- [ ] Can configure groups and permissions
- [ ] Can set up processes
- [ ] Can configure master data
- [ ] Understands system monitoring
- [ ] Can troubleshoot common issues

---

## Quick Reference

### Create User
Users → **+ New** → Fill details → Assign groups → **Save**

### Create Group
Groups → **+ New** → Name group → **Save** → Assign permissions

### Deactivate User
Open user → Uncheck **Active** → **Save**

### Review Audit Log
Admin → Audit Log → Filter as needed → Export if required

### Troubleshoot Access
Check: User active? → In groups? → Group has permission? → Role type allows?

---

## Next Steps

After completing this training:

1. Shadow current administrator
2. Handle user requests with oversight
3. Configure non-critical items independently
4. Full administrative responsibility

---

## Emergency Contacts

Document these for your organization:

- **Platform support:** [Your support channel]
- **IT escalation:** [IT contact]
- **Management:** [Management contact]
- **Security incidents:** [Security contact]

