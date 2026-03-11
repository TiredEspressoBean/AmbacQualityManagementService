# Training Data Setup Guide

**Audience:** System Administrators
**Purpose:** Set up a training environment with realistic demo data for hands-on exercises

---

## Overview

Training exercises require realistic data to be meaningful. This guide explains how to populate your training environment with demo data that matches the examples used throughout the training guides.

## Option 1: Use Demo Mode (Recommended)

If your organization has demo mode enabled, training data is pre-populated automatically.

### Demo Accounts

All demo accounts use password: `demo123`

| Role | Email | Name | Training Guide |
|------|-------|------|----------------|
| Administrator | admin@demo.ambac.com | Alex Demo | [Administrator Guide](administrator.md) |
| QA Manager | maria.qa@demo.ambac.com | Maria Santos | [QA Manager Guide](qa-manager.md) |
| QA Inspector | sarah.qa@demo.ambac.com | Sarah Chen | [QA Inspector Guide](qa-inspector.md) |
| Production Manager | jennifer.mgr@demo.ambac.com | Jennifer Walsh | [Production Manager Guide](production-manager.md) |
| Operator | mike.ops@demo.ambac.com | Mike Rodriguez | [Operator Guide](operator.md) |
| Operator (Expired Training) | dave.wilson@demo.ambac.com | Dave Wilson | Training compliance demo |
| Document Controller | lisa.docs@demo.ambac.com | Lisa Park | [Document Controller Guide](document-controller.md) |
| Customer Portal | tom.bradley@midwestfleet.com | Tom Bradley | [Customer Guide](../roles/customer.md) |

### Demo Data Included

| Category | Examples |
|----------|----------|
| **Orders** | ORD-2024-0042 (in progress), ORD-2024-0038 (completed), ORD-2024-0048 (pending) |
| **Parts** | INJ-0042-001 through INJ-0042-024 (various statuses) |
| **Work Orders** | WO-0042-A (67% complete) |
| **Quality Reports** | QR-2024-0187 (nozzle defects) |
| **Dispositions** | QD-2024-0001 (Rework), QD-2024-0002 (Use As Is), QD-2024-0003 (Scrap) |
| **CAPA** | CAPA-2024-003 (nozzle defect investigation) |
| **Equipment** | Flow Test Stand #1, #2, Torque Wrench TW-25 (overdue calibration) |
| **Customers** | Midwest Fleet (Tom Bradley), Northern Trucking Co |

---

## Option 2: Run Population Command

For self-hosted installations, use the management command to generate training data.

### Prerequisites

- Database access
- Django management command access
- Superuser or admin permissions

### Running the Command

```bash
# Recommended: Demo mode with preset training data
python manage.py seed_demo

# Dev mode with random data (for development/testing)
python manage.py seed_dev

# Both demo and dev tenants
python manage.py seed_all

# Keep existing data (don't clear first)
python manage.py seed_demo --no-clear

# Larger dev dataset
python manage.py seed_dev --scale medium

# Preview what would be created (dry run)
python manage.py seed_demo --dry-run

# Seed specific modules only (dev mode)
python manage.py seed_dev --modules users manufacturing orders
```

### Command Options

| Command | Tenant | Data Type | Use Case |
|---------|--------|-----------|----------|
| `seed_demo` | Demo Company | Deterministic, preset users | Training, sales demos |
| `seed_dev` | Development | Random Faker data | Development, testing |
| `seed_all` | Both | Both types | Full environment setup |

### Scale Options

| Scale | Orders | Parts | Use Case |
|-------|--------|-------|----------|
| `small` | ~10 | ~100 | Quick setup, individual training (default) |
| `medium` | ~50 | ~500 | Standard training |
| `large` | ~200 | ~2000 | Load testing, comprehensive demos |

### What Gets Created

The command creates:

1. **Users** - Demo accounts for each role
2. **Customers** - Sample companies
3. **Part Types** - Common Rail Injector, HEUI Injector, Unit Injector
4. **Processes** - Manufacturing workflows with steps
5. **Orders & Work Orders** - In various states
6. **Parts** - Distributed across workflow steps
7. **Quality Reports** - Sample NCRs with dispositions
8. **CAPA** - Active investigation with tasks
9. **Documents** - Sample work instructions
10. **Equipment** - With calibration records (including overdue)
11. **Training Records** - Including expired certifications
12. **Measurement Data** - For SPC charts

---

## Option 3: Manual Setup

For customized training scenarios, create data manually.

### Minimum Required Data

For basic training exercises, create:

#### 1. Users (one per role being trained)

Navigate to **Data Management > Users**:

| User | Groups | Purpose |
|------|--------|---------|
| Training Operator | Production_Operator | Operator exercises |
| Training Inspector | QA_Inspector | Inspector exercises |
| Training Manager | Production_Manager | Manager exercises |

#### 2. Customer

Navigate to **Data Management > Companies**:
- Name: Training Customer
- Type: Customer

#### 3. Part Type

Navigate to **Data Management > Part Types**:
- Name: Training Part
- Part Number: TRAIN-001
- Default Process: (select existing process)

#### 4. Order with Parts

Navigate to **Data Management > Orders**:
1. Create order (e.g., TRAIN-ORD-001)
2. Add 10 parts with serial prefix TRAIN-

#### 5. Work Order

Navigate to **Production > Work Orders**:
- Link to order
- Assign to process

### Creating Specific Scenarios

#### Scenario: Parts for Inspection

1. Create parts that have passed through early steps
2. Leave them at an inspection step
3. Inspector can practice recording measurements

#### Scenario: FPI Pending

1. Start a new batch
2. First part reaches FPI-required step
3. Remaining parts are held automatically

#### Scenario: Quarantined Parts

1. Create quality report for a part
2. Select QUARANTINED status
3. Part available for disposition practice

#### Scenario: CAPA Investigation

1. Navigate to Quality > CAPAs
2. Create CAPA with type: Corrective
3. Add tasks for training exercises

---

## Data for Specific Training Modules

### Operator Training

**Minimum data needed:**
- [ ] 1 order with 10+ parts
- [ ] Work order linked to a process
- [ ] Parts distributed across steps (some to move)

**Exercise support:**
- Parts at various steps for moving forward
- At least one FPI-required step with first part pending

### QA Inspector Training

**Minimum data needed:**
- [ ] Parts at inspection steps
- [ ] Measurement definitions with specs
- [ ] Quality report examples

**Exercise support:**
- Parts ready for measurement recording
- Sample NCR to review
- Disposition pending for recommendation

### QA Manager Training

**Minimum data needed:**
- [ ] Open CAPA with tasks
- [ ] Pending disposition approvals
- [ ] Document awaiting approval

**Exercise support:**
- CAPA in various states (one open, one pending verification)
- Quality reports needing disposition decision

### Production Manager Training

**Minimum data needed:**
- [ ] Multiple orders in progress
- [ ] Work orders at various stages
- [ ] Equipment records

**Exercise support:**
- Orders with different priorities
- Bottleneck visible (parts stuck at step)

### SPC Training

**Minimum data needed:**
- [ ] 50+ measurement results for one definition
- [ ] Measurements spanning 30+ days
- [ ] Mix of normal and out-of-control points

**Exercise support:**
- Frozen SPC baseline
- At least one out-of-control signal visible

### Document Controller Training

**Minimum data needed:**
- [ ] Draft document for upload exercise
- [ ] Document pending approval
- [ ] Document revision history

**Exercise support:**
- Document for revision exercise
- Approval workflow examples

---

## Exercise Data Matrix

This matrix lists all specific training records referenced in exercise instructions. These records should be created by the `seed_demo` command.

### Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| TRAIN-001 | Basic operator training order | Operator | In progress, 10 parts at various steps |
| TRAIN-PM-001 | Production manager exercise order | Production Manager | Pending, 5 parts ready to process |
| TRAIN-BOTTLE | Bottleneck scenario | Production Manager | In progress, 8 parts stuck at one step |
| TRAIN-HOLD | Quality hold scenario | Production Manager | On hold for QA issue, 6 parts |
| TRAIN-FPI-001 | FPI training exercise | QA Inspector | In progress, 15 parts awaiting FPI |

### Assessment Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| ASSESS-001 | Operator assessment - find and track order | Operator | In progress, 6 parts distributed |
| ASSESS-003 | Operator assessment - specific part lookup | Operator | In progress, 5 parts distributed |
| ASSESS-004 | Operator assessment - search exercise | Operator | Pending, 4 parts |
| ASSESS-QA-001 | QA Inspector assessment - FPI completion | QA Inspector | In progress, 10 parts for FPI |
| ASSESS-QA-002 | QA Inspector assessment - sampling inspection | QA Inspector | In progress, 12 parts for sampling |
| ASSESS-PM-001 | Production manager assessment - order management | Production Manager | Pending, 8 parts |

### Work Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| TRAIN-FPI-001 | FPI training work order | QA Inspector | In progress, first piece awaiting inspection |
| ASSESS-QA-001 | QA Inspector assessment - FPI completion | QA Inspector | In progress, 10 parts for FPI exercise |
| ASSESS-QA-002 | QA Inspector assessment - sampling inspection | QA Inspector | In progress, 12 parts for sampling exercise |

### Parts

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| TRAIN-101-003 | Part for quality report exercise (surface scratch) | QA Inspector | At inspection step with defect |
| TRAIN-101-005 | Part for quality report exercise (flow test failure) | QA Inspector | At inspection step with defect |
| TRAIN-001-* | Parts in TRAIN-001 order (10 total) | Operator | Distributed across process steps |
| ASSESS-003-002 | Part for operator assessment lookup exercise | Operator | At inspection step |

### Quality Reports

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| QR-TRAIN-001 | Review exercise quality report | QA Inspector | Open, pending review |
| QR-TRAIN-002 | Disposition recommendation exercise | QA Inspector | Open, needs disposition |
| QR-ASSESS-001 | Assessment - dimensional out of tolerance | QA Inspector | Failed, for assessment exercise |
| QR-ASSESS-002 | Assessment - visual defect found | QA Inspector | Failed, for assessment exercise |

### Dispositions

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| DISP-TRAIN-001 | Pending approval exercise | QA Manager | Pending approval (rework) |
| DISP-TRAIN-002 | Rejection exercise | QA Manager | Pending (should be rejected - incomplete info) |
| DISP-ASSESS-001 | Assessment disposition - rework recommendation | QA Manager | In progress, ready for approval |

### CAPAs

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| CAPA-TRAIN-COMPLETE | Verification closure exercise | QA Manager | Pending verification, all tasks complete |
| CAPA-ASSESS-READY | Assessment CAPA - ready for closure verification | QA Manager | Pending verification, all actions complete |

### Documents

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| WI-TRAIN-001 | Work instruction exercise | Document Controller, QA Manager | Pending approval |
| DOC-REJECT-TRAIN | Rejection scenario document | Document Controller | Pending (should be rejected) |

---

## Verifying Training Data

After setup, verify data is ready:

### Quick Checks

```bash
# Count records (if using command line)
python manage.py shell -c "
from Tracker.models import *
print(f'Users: {User.objects.count()}')
print(f'Orders: {Orders.objects.count()}')
print(f'Parts: {Parts.objects.count()}')
print(f'Quality Reports: {QualityReports.objects.count()}')
print(f'CAPAs: {CAPA.objects.count()}')
"
```

### UI Verification

| Check | Navigate To | Expected |
|-------|-------------|----------|
| Orders exist | Tracker | See order cards |
| Parts distributed | Order detail | Parts at various steps |
| Quality reports | Quality > Quality Reports | Sample NCRs visible |
| CAPA active | Quality > CAPAs | At least one open |
| Equipment | Data Management > Equipment | Items with calibration |
| SPC data | Tools > Analytics > SPC | Chart displays with points |

---

## Resetting Training Data

To reset between training sessions:

### Option A: Clear and Repopulate

```bash
# Reset demo tenant (recommended for training)
python manage.py seed_demo

# Reset both tenants
python manage.py seed_all
```

This clears existing data (except platform admin) and recreates fresh.

### Option B: Reset Specific Records

For targeted reset:

1. Delete completed exercises (orders, quality reports)
2. Reset part statuses to earlier steps
3. Reopen closed CAPAs

### Option C: Database Restore

If using a training database backup:

```bash
# Restore from backup (PostgreSQL example)
pg_restore -d ambac_training training_backup.dump
```

---

## Separating Training from Production

### Recommended: Separate Tenant

Create a dedicated training tenant:
- Isolated from production data
- Can be reset without affecting real work
- Users can make mistakes safely

### Alternative: Training Flag

If using same database:
- Create orders with prefix "TRAIN-"
- Use dedicated training customer
- Filter by prefix in production views

---

## Troubleshooting

### No data appears after command

1. Check command completed without errors
2. Verify correct tenant/database
3. Check user has permission to view data

### SPC charts empty

1. Verify measurement results exist
2. Check date range includes data period
3. Confirm measurement definition has SPC enabled

### Users can't log in

1. Verify user accounts were created
2. Check passwords were set
3. Confirm group assignments

### Parts won't move

1. Check required measurements are defined
2. Verify FPI requirements
3. Confirm user has permissions

---

## Support

For issues with training data setup:
1. Check this guide's troubleshooting section
2. Review command output for errors
3. Contact system administrator
