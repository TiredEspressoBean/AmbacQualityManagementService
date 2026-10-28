# Training Program

Hands-on training for each role, built around one working day at a fictional
shop. The help docs explain how each part of uqmes works; training is where you
practise doing it, on data made for practising.

!!! warning "Train on a training instance, never on your live system"
    Training runs on a **separate uqmes instance** seeded with the training shop,
    and no real company data goes into it. Every exercise writes real records:
    a practice FAIL quarantines a part and opens a disposition, a practice PASS
    clears a gate, notifications fire, and signatures can't be undone. On a live
    system those records would be false, and in a tightly linked supply chain a
    false pass or fail travels downstream.

## How it fits together

| Part | What it is |
|---|---|
| [The Shop Day](shop-day.md) | One working day at the training shop, with every role's moments and the handoffs between them. Every track is a slice of it |
| **Role tracks** | One per role: exercises on the shop day, ending in a final task your trainer watches you do |
| **Running training** | For whoever runs training at your site: loading the training shop onto the training instance |

Roles compose. Someone who is a QA Inspector by day and a Shift Lead when covering
takes both tracks, and each teaches only what that role adds.

!!! info "If your organisation runs change control in Simplified mode"
    Change control can run **Regulated** (signed approvals across roles) or
    **Simplified** (one-click approval). See [Change
    Control](../workflows/change-control/overview.md#simplified-or-regulated).
    Where the two differ, a track gives both paths. Follow the one your
    organisation uses.

!!! info "If your shop remanufactures"
    Each track is written for **new manufacture**. Where remanufacturing adds work
    for a role (cores, teardown, harvested components, rebuilds), the track ends
    with an *If your shop remanufactures* section. A shop that only builds new skips
    it.

## Role tracks

| Role | Track |
|---|---|
| Operator | [Operator](tracks/operator.md) |
| Shift Lead | [Shift Lead](tracks/shift-lead.md) |
| QA Inspector | [QA Inspector](tracks/qa-inspector.md) |
| QA Manager | [QA Manager](tracks/qa-manager.md) |
| Production Manager | [Production Manager](tracks/production-manager.md) |
| Planner | [Planner](tracks/planner.md) |
| Engineering | [Engineering](tracks/engineering.md) |
| Purchasing | [Purchasing](tracks/purchasing.md) |
| Receiving | [Receiving](tracks/receiving.md) |
| Shipping | [Shipping](tracks/shipping.md) |
| Document Controller | [Document Controller](tracks/document-controller.md) |
| Administrator | [Administrator](tracks/administrator.md) |

**Orientation, not training:** [Auditor](tracks/auditor.md) (no write
permissions to practise) and [Customer Portal](tracks/customer.md) (external).

**Across roles:** [SPC Fundamentals](tracks/spc-fundamentals.md).

## Running training

- [Training Data Setup](running-training/training-data-setup.md): loading the
  training shop onto the training instance.

## Getting help during training

- Your super-user or trainer first
- The [Role Guides](../roles/index.md) and help pages for how something works
- [Troubleshooting](../troubleshooting/common-issues.md) for common problems
