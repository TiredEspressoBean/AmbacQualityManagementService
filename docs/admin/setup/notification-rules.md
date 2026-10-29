# Notification Rules

Notification rules decide **who gets told when something happens**. They are
declarative: an event occurs, matching rules fire, and the people each rule
names are notified on the channels it lists.

**Admin** > **Settings** > **Notifications** (`/settings/notification-rules`)

The page has two tabs:

- **Rules** — event-driven. Something happened, tell someone.
- **Schedules** — recurring digests on a timetable.

## Scopes

Every rule belongs to one of three scopes, shown as tabs:

| Scope | Authored by | Fires for |
|-------|-------------|-----------|
| **Tenant-wide** | Tenant Admin, QA Manager, Production Manager | Any matching event across the organization |
| **Customer-scoped** | Tenant Admin, QA Manager, Production Manager | Events concerning one specific customer |
| **Personal** | The individual user | That user's own notifications |

All three are evaluated for a given event, so a tenant rule and someone's
personal rule can both fire on the same thing.

## Anatomy of a rule

| Field | What it does |
|-------|--------------|
| **Name** | How the rule appears in the list |
| **Event** | Which event it listens for |
| **Condition** | An optional condition tested against the event — shown in the list's **When** column, as `always` when there is none |
| **Recipients** | Users, groups, or (customer scope only) external contacts |
| **Channels** | Where the notification goes — for example in-app, email |
| **Active** | Whether it fires at all |

A rule also stores a **priority** and a **minimum gap** (which suppresses repeat
notifications from the same rule inside a time window), but the rule editor has
no control for either. A rule created here, and every starter rule, has a
minimum gap of 0 — no suppression.

### Conditions

The **When** column is `always` for an unconditional rule. A conditional rule
carries an expression evaluated against the event's data, so you can route (for
example) only high-priority work orders, or only one customer's orders, without
creating a separate event.

## Starter rules

!!! warning "Nothing here is guaranteed"
    These are **seeded defaults, not behaviour**. Every one can be edited,
    disabled, or deleted, and most deployments do change them. Delivery is
    driven entirely by the rules that exist in *this* tenant right now — so
    never assume a notification went out because a document says it should
    have.

    If it matters that somebody was told, check the rule.

A tenant is seeded in two passes when it is created.

**Hand-picked rules**, chosen because the routing is obvious:

| Event | Routes to |
|-------|-----------|
| NCR opened | QA Manager |
| Step failure | QA Manager and QA Inspector |
| CAPA assigned or reassigned | The assignee |
| CAPA ready for effectiveness verification | QA Manager |
| Work order overdue | Production Manager |
| Work order held too long | Production Manager |
| Training expiring soon | QA Manager, Production Manager, and the operator |
| Training expired | QA Manager, Production Manager, and the operator |
| Shift note posted | The note's audience |

**Everything else** is filled in from each event's own default recipient
groups — this is where rules like *First Piece Waiting* and *Unapproved Part
Receipt* come from. An event that declares no defaults gets **no rule at all**,
and so notifies nobody until someone writes one.

!!! note "Re-seeding restores a renamed starter rule"
    Seeding skips a starter rule when a rule with the same event and the same
    name already exists — and a deleted rule still counts, because delete
    archives it rather than removing it. So deleting or disabling a starter rule
    retires it for good. **Renaming** one does not: the next time seeding runs,
    the original name is missing and the starter rule is created again beside
    yours.

!!! tip "Backfilling existing tenants"
    Tenants created before the starter set existed can be backfilled by an
    administrator running `setup_notification_rules`.

## Creating a rule

1. Go to **Admin** > **Settings** > **Notifications**
2. Choose the scope tab you're authoring in
3. Click **New rule**
4. Pick the event, set any condition, choose recipients and channels
5. Click **Create rule**

## Schedules

The **Schedules** tab handles recurring digests rather than event reactions —
a weekly or monthly summary sent on a timetable. Schedules have two scope tabs,
**Tenant-wide** and **Customer-scoped** — there are no personal schedules.

!!! note "Schedules don't deliver reports"
    Notification schedules send notification digests. They do not generate or
    email PDF reports — report scheduling is a separate, still-planned feature.
    See [Compliance Reports](../../compliance/reports.md).

## Your own notifications

Individual users manage their personal rules and preferences from **My
Notifications** in the sidebar profile menu (`/profile/notifications`), not from
this page.

## Next Steps

- **[Change Control](../../workflows/change-control/overview.md)** - PCN release routing uses these rules
- **[Administrator Guide](../../roles/administrator.md)** - The rest of system configuration
