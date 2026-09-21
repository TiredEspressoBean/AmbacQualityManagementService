# Getting Help

!!! warning "There is no support desk"
    uqmes has no vendor support line, no ticketing system, no service-level
    agreement, and no account manager. Nothing in this system pages anyone.

    If something is broken, the resources below are what exist. Escalation
    means telling whoever runs uqmes for your organization — in person, or
    however you normally reach them.

## Work the problem yourself first

Most of what goes wrong is already written down, and usually under a heading
that names the symptom rather than the cause.

| Resource | Use it for |
|----------|------------|
| **[Common Issues](common-issues.md)** | A concrete symptom — a part that won't move, an error message, a page that won't load |
| **[FAQ](faq.md)** | "Is it supposed to work like this?" |
| The rest of these docs | How a feature is meant to be used |

Search is the fastest way in. If you are looking at an error, **search the
exact words on screen** — the docs quote real messages, so the text you are
staring at is often the best query.

### AI Chat

**AI Chat** in the sidebar can answer questions about your own data and about
how features work. It is a way to explore the system, not a support channel —
nobody is notified by it, and it cannot change anything or escalate on your
behalf.

## When you do need a person

There is no support organization, so the person who can help is whoever
administers this deployment. Who that is depends on your site — these docs
cannot tell you.

Roughly, problems sort into:

| Symptom | Usually |
|---------|---------|
| You can't see or do something you expect to | A permissions or assignment question — see [Assigning Permissions](../admin/users/permissions.md) |
| A record is wrong and you can't correct it | Usually deliberate: quality records are voided or superseded, not edited |
| Login or SSO fails | A configuration question for whoever set up the identity provider |
| Something is genuinely broken | Whoever maintains the system |

!!! tip "Check permissions before reporting a bug"
    "The button isn't there" is far more often a permission or assignment than
    a fault. A newly granted permission also needs
    `sync_tenant_permissions` on an existing tenant — see [Existing tenants and
    new permissions](../admin/users/permissions.md#existing-tenants-and-new-permissions).

## Writing a report worth reading

Whoever you tell, these are what turn "it's broken" into something fixable:

1. **The exact error text**, copied rather than paraphrased
2. **What you were doing** — the page, the record, the button
3. **The record's identifier** — the work order, part serial, or document number
4. **What you expected instead**, which is often the part that reveals the
   real disagreement
5. **Whether it happens every time** or happened once
6. **Your role**, since a great many "bugs" are permissions

A screenshot covers most of the first three at once.

## Urgent situations

Nothing here pages anyone, so "urgent" means *what you should do*, not who to
call.

**Suspected data problem** — stop the work that is producing it. Do not try to
correct records to tidy up; in a quality system the wrong record plus its
correction is evidence, and a quietly fixed record is not. Note what happened
and when, then raise it.

**Suspected security problem** — report it to whoever administers the system
straight away, and write down what you saw. Do not investigate by reproducing
it.

**Nonconforming product** — that is not a support issue. Contain it and raise
it through the quality system: see [Flagging
Issues](../workflows/tracking/flagging-issues.md) and
[Dispositions](../workflows/quality/dispositions.md).

## Have ready

- Your username and role
- The work order, part, or document identifier
- Browser and version
- When it happened
- Any error text or codes

## Useful Links

- [Common Issues](common-issues.md)
- [FAQ](faq.md)
- [Glossary](../getting-started/glossary.md)
- [Navigation Guide](../getting-started/navigation.md)
