# Training Data Setup Guide

**Audience:** System Administrators
**Purpose:** Set up a training environment with realistic demo data for hands-on exercises

---

## Overview

Training exercises require realistic data to be meaningful. This guide explains how to populate your training environment with demo data that matches the examples used throughout the training guides.

## Option 1: Seed the Demo Tenant (Recommended)

Run `python manage.py seed_demo` on the training instance (see [Option
2](#option-2-run-population-command)). It creates the demo tenant, its accounts and
the training shop. Nothing is populated until it runs.

### Demo Accounts

All demo accounts use password: `demo123`

| Role | Email | Name | Training Guide |
|------|-------|------|----------------|
| Administrator | admin@demo.ambac.com | Alex Demo | [Administrator Guide](../tracks/administrator.md) |
| QA Manager | maria.qa@demo.ambac.com | Maria Santos | [QA Manager Guide](../tracks/qa-manager.md) |
| QA Inspector | sarah.qa@demo.ambac.com | Sarah Chen | [QA Inspector Guide](../tracks/qa-inspector.md) |
| Production Manager | jennifer.mgr@demo.ambac.com | Jennifer Walsh | [Production Manager Guide](../tracks/production-manager.md) |
| Operator | mike.ops@demo.ambac.com | Mike Rodriguez | [Operator Guide](../tracks/operator.md) |
| Operator (Expired Training) | dave.wilson@demo.ambac.com | Dave Wilson | Training compliance demo |
| Document Controller | lisa.docs@demo.ambac.com | Lisa Park | [Document Controller Guide](../tracks/document-controller.md) |
| Customer Portal | tom.bradley@midwestfleet.com | Tom Bradley | [Customer Guide](../../roles/customer.md) |

### Demo Data Included

| Category | Examples |
|----------|----------|
| **Orders** | ORD-2024-0042 (in progress), ORD-2024-0038 (completed), ORD-2024-0048 (pending) |
| **Parts** | INJ-0042-001 through INJ-0042-024 (various statuses) |
| **Work Orders** | WO-2024-0042-A, WO-2024-0038-A, WO-2024-0048-A, plus WO-QA-INSPECT-01 to -06 and WO-QA-MANAGE-01 (the QA exhibits) |
| **Quality Reports** | QR-0042-001-FT, QR-0038-003-NI — both are Flow Calibration reports |
| **Dispositions** | The QA Inspector exhibits' rework on INJ-QA-INSPECT-013, plus the history the quality seeder writes |
| **CAPA** | CAPA-2024-003 (nozzle defect investigation) |
| **Equipment** | Flow Test Stand #1, #2, Torque Wrench TW-25 (overdue calibration) |
| **Customers** | Midwest Fleet (Tom Bradley), Northern Trucking Co |

---

## Option 2: Run Population Command

For self-hosted installations, use the management command to generate training data.

### Prerequisites

- Database access
- Django management command access
- The database user must be a **PostgreSQL superuser**: clearing the demo data
  first (the default) needs it

!!! danger "Only on a training or demo instance"
    Clearing before a reseed also clears the audit log for **every**
    organization on the instance, not just the demo one. Run `seed_demo` only
    on an instance that holds no real company's data.

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
| `small` | ~10 | ~100 | Quick setup (default) |
| `medium` | ~50 | ~1,000 | Larger dev dataset |
| `large` | ~200 | ~6,500 | Load testing |

Scale applies to `seed_dev` only; `seed_demo` always creates the same shop.

### What Gets Created

The command creates:

1. **Users** - Demo accounts for each role
2. **Customers** - Sample companies
3. **Part Types** - Common Rail Injector (`seed_dev` adds HEUI and Unit Injector)
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

Navigate to **Admin** > **User Management**:

| User | Groups | Purpose |
|------|--------|---------|
| Training Operator | Operator | Operator exercises |
| Training Inspector | QA Inspector | Inspector exercises |
| Training Manager | Production Manager | Manager exercises |

#### 2. Customer

Navigate to **Data Management > Companies**:
- Name: Training Customer
- Type: Customer

#### 3. Part Type

Navigate to **Data Management > Part Types**:
- Name: Training Part
- ERP ID: TRAIN-001

A part type carries no process; each process names the part type it is for.

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
2. Set its status to FAIL: the part is quarantined and a disposition opens
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

**Exercise support:** WO-QA-INSPECT-01 to -06 and WO-QA-MANAGE-01 — see the
[shop day](../shop-day.md) and the [QA Inspector track](../tracks/qa-inspector.md).

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

These are the legacy exercise records `seed_demo` creates; the role tracks name their own exhibits.

### Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| TRAIN-001 | Basic operator training order | Operator | In progress, 10 parts at various steps |
| TRAIN-PM-001 | Production manager exercise order | Production Manager | Pending, 5 parts ready to process |
| TRAIN-BOTTLE | Bottleneck scenario | Production Manager | In progress, 6 of 8 parts stuck at one step |
| TRAIN-HOLD | Quality hold scenario | Production Manager | On hold for QA issue, 6 parts |

### Assessment Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| ASSESS-001 | Operator assessment - find and track order | Operator | In progress, 6 parts distributed |
| ASSESS-003 | Operator assessment - specific part lookup | Operator | In progress, 5 parts distributed |
| ASSESS-004 | Operator assessment - search exercise | Operator | Pending, 4 parts |
| ASSESS-PM-001 | Production manager assessment - order management | Production Manager | Pending, 8 parts |

### Work Orders

| ID | Description | Used By | State |
|----|-------------|---------|-------|

### Parts

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| TRAIN-001-* | Parts in TRAIN-001 order (10 total) | Operator | Distributed across process steps |
| ASSESS-003-002 | Part for operator assessment lookup exercise | Operator | At an early working step |

### CAPAs

| ID | Description | Used By | State |
|----|-------------|---------|-------|
| CAPA-TRAIN-COMPLETE | Verification closure exercise | QA Manager | Pending verification, all tasks complete |
| CAPA-ASSESS-READY | Assessment CAPA - ready for closure verification | QA Manager | Pending verification, all actions complete |

---

## Verifying Training Data

After setup, verify data is ready:

### Quick Checks

```bash
# Count records (if using command line)
python manage.py shell -c "
from Tracker.models import *
from Tracker.utils.tenant_context import tenant_context
t = Tenant.objects.get(slug='demo')
with tenant_context(t.id):
    print(f'Users: {User.objects.filter(tenant=t).count()}')
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
| SPC data | Analytics > **SPC** (on the FPY Trend card) | Chart displays with points |

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

This clears existing data (except platform admin) and recreates fresh —
including the instance's whole audit log, so only on a training instance.

### Option B: Reset Specific Records

There isn't one. Exercises write evidence, and evidence can't be put back: a recorded
quality report is final, a closed CAPA can't be edited or reopened by hand, and a
part with an open disposition changes status only through it. Regenerate (Option A)
instead.

### Option C: Database Restore

If using a training database backup:

```bash
# Restore from backup (PostgreSQL example)
pg_restore -d ambac_training training_backup.dump
```

---

## Separating Training from Production

Training runs on a separate uqmes instance seeded with `seed_demo`. No company
data goes into it, and it is reset by regenerating the demo data. See the
[training program](../index.md).

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

1. Check the step's work instruction: a required field left empty keeps the step
   from completing, and a step with **Block on out-of-spec measurement** on holds a
   part whose reading is out of specification
2. Verify FPI requirements
3. Confirm user has permissions

---

## Support

For issues with training data setup:
1. Check this guide's troubleshooting section
2. Review command output for errors
3. Contact system administrator
