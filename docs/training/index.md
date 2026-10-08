# Training Program

Welcome to the uqmes training program. These guides provide structured onboarding for each role, with hands-on exercises and knowledge checks.

## Training Philosophy

Our training is:

- **Role-based**: Learn what you need for your job
- **Hands-on**: Practice in a training environment
- **Progressive**: Build skills step by step
- **Validated**: Confirm understanding with exercises

## Available Training

| Role | Duration | Prerequisites |
|------|----------|---------------|
| [Production Operator](operator.md) | 2-4 hours | None |
| [Shift Lead](shift-lead.md) | 3-4 hours | Operator training |
| [QA Inspector](qa-inspector.md) | 4-6 hours | None |
| [QA Manager](qa-manager.md) | 4-6 hours | Inspector training recommended |
| [Production Manager](production-manager.md) | 3-5 hours | None |
| [Planner](planner.md) | 4-5 hours | None |
| [Engineering](engineering.md) | 4-5 hours | None |
| [Purchasing](purchasing.md) | 3-4 hours | None |
| [Receiving](receiving.md) | 3-4 hours | None |
| [Shipping](shipping.md) | 2-3 hours | None |
| [Document Controller](document-controller.md) | 3-4 hours | None |
| [Administrator](administrator.md) | 6-8 hours | Understanding of all roles |

### Orientation, not training

Two roles need showing around rather than teaching. Neither has anything to
practise — one cannot write at all, the other is external.

| Role | Duration | For |
|------|----------|-----|
| [Auditor](auditor.md) | 1 hour | Internal and external auditors |
| [Customer Portal](customer.md) | 30 min | Hand this to your customer |

!!! info "Roles compose, and so does their training"
    Holding more than one group is normal. A QA Inspector who is also a Shift
    Lead takes both tracks — Shift Lead assumes Operator and teaches only what is
    added on top, rather than repeating it.

## Cross-Cutting Modules

These supplemental modules cover topics that apply across multiple roles:

| Module | Duration | Recommended For |
|--------|----------|-----------------|
| [SPC Fundamentals](spc-fundamentals.md) | 1-2 hours | Operators, QA Inspectors, QA Managers, Production Managers |
| [Training Data Setup](training-data-setup.md) | 30 min | Administrators setting up training environments |

## Specialized Workflows

The following workflows have dedicated documentation:

| Workflow | Documentation | Description |
|----------|--------------|-------------|
| Remanufacturing | [Reman Overview](../workflows/reman/overview.md) | Core receiving, disassembly, and component harvesting |
| Life Tracking | [Life Tracking Guide](../workflows/tracking/life-tracking.md) | Monitoring cycles, hours, shelf life, and limits |

Remanufacturing is fully operational. Life tracking core functionality works (viewing status on parts), but dedicated reporting pages are planned.

!!! tip "SPC Training"
    All production floor staff should complete **SPC Fundamentals** to understand control charts and process capability. This is referenced throughout the role-specific training guides.

!!! info "Every role group now has a track"
    All 15 permission presets are covered. **System Admin** and **Tenant Admin**
    are both served by [Administrator training](administrator.md); every other
    group has its own page above.

    There is **no "Supplier Quality" group**, despite older documentation saying
    so. That work splits between [Purchasing](purchasing.md) and
    [QA Manager](qa-manager.md), who holds the approval authority.

!!! warning "Most tracks log in as a broader account"
    The demo seeds accounts for Operator, Shift Lead, QA Inspector, QA Manager,
    Production Manager, Document Controller, Tenant Admin and Customer only.

    Planner, Engineering, Purchasing, Receiving, Shipping and Auditor training
    therefore signs in as **Tenant Admin** or **Production Manager**, which hold
    those permissions plus more. Everything in those guides works — but the
    screen will show more than the guide describes, and the trainee will not
    experience the role's real boundaries. Seed a dedicated account before
    running them for real.

## Training Environment

Your organization should provide a training environment where you can:

- Practice without affecting production data
- Make mistakes safely
- Explore features freely

!!! warning "Training vs Production"
    Always confirm you're in the training environment before practicing. Look for visual indicators like a banner or different color scheme.

## How Training Works

### 1. Read the Guide

Each training guide covers:

- Core concepts
- Step-by-step procedures
- Best practices
- Common mistakes to avoid

### 2. Complete Exercises

Hands-on exercises let you practice:

- [ ] Exercise has clear objectives
- [ ] Step-by-step instructions provided
- [ ] Expected results described

### 3. Knowledge Check

Each section includes questions to verify understanding.

### 4. Competency Sign-Off

After completing training:

1. Demonstrate skills to supervisor
2. Complete any required assessments
3. Receive system access for your role

## Training Records

Your training completion is tracked in the system:

- Training date
- Modules completed
- Supervisor sign-off
- Retraining dates (if applicable)

!!! example "Demo: Expired Training Alert"
    In demo mode, operator **Dave Wilson** has an expired training record:

    - Flow Testing Certification expired 45 days ago
    - System blocks him from working at Flow Testing step
    - Production Manager Jennifer Walsh sees the alert in her dashboard
    - Dave must complete retraining before resuming Flow Testing work

    This demonstrates how the system enforces training requirements at production steps.

## Getting Help During Training

- Ask your trainer or supervisor
- Use the training environment to experiment
- Refer to the [Role Guides](../roles/index.md) for reference
- Check [Troubleshooting](../troubleshooting/common-issues.md) for common issues

## Retraining

Retraining may be required when:

- System features change significantly
- Processes are updated
- After extended absence
- Following quality issues
- Per regulatory requirements
- **Training certification expires** (see Dave Wilson example above)

## For Trainers

If you're conducting training:

1. Ensure training environment is set up (see [Training Data Setup](training-data-setup.md))
2. Review training guide beforehand
3. Assign [SPC Fundamentals](spc-fundamentals.md) for production floor roles
4. Allow time for questions and practice
5. Document completion
6. Verify competency before production access

