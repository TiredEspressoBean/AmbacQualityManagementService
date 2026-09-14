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
| **Tenant-wide** | Administrators | Any matching event across the organization |
| **Customer-scoped** | Administrators | Events concerning one specific customer |
| **Personal** | The individual user | That user's own notifications |

All three are evaluated for a given event, so a tenant rule and someone's
personal rule can both fire on the same thing.

## Anatomy of a rule

| Field | What it does |
|-------|--------------|
| **Name** | How the rule appears in the list |
| **Event** | Which event it listens for |
| **When** | An optional condition — `always`, or an expression tested against the event |
| **Recipients** | Users, groups, or (customer scope only) external contacts |
| **Channels** | Where the notification goes — for example in-app, email |
| **Active** | Whether it fires at all |

Rules also carry a **priority** and a **minimum gap**, which suppresses repeat
notifications from the same rule inside a time window — useful for noisy events.

### Conditions

The **When** column is `always` for an unconditional rule. A conditional rule
carries an expression evaluated against the event's data, so you can route (for
example) only high-priority work orders, or only one customer's orders, without
creating a separate event.

## Starter rules

New tenants get a set of starter rules covering the common routing:

| Rule | Routes |
|------|--------|
| First Piece Waiting / First Piece Decided | Production Manager |
| Unapproved Part Receipt | Default recipients |
| Shift notes | The shift-note audience |
| Held work orders | Production |
| Overdue work orders | Production |
| CAPA assignments | The assignee |
| Step failures | QA |
| NCRs | QA Manager |

!!! tip "Backfilling existing tenants"
    Tenants created before the starter set existed can be backfilled by an
    administrator running `setup_notification_rules`.

## Creating a rule

1. Go to **Admin** > **Settings** > **Notifications**
2. Choose the scope tab you're authoring in
3. Click **New rule**
4. Pick the event, set any condition, choose recipients and channels
5. Save

## Schedules

The **Schedules** tab handles recurring digests rather than event reactions —
a daily or weekly summary sent on a timetable. Schedules are scoped the same way
rules are.

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
