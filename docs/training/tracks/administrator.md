# Administrator

The tenant administrator's slice of [the shop day](../shop-day.md): giving people the
access their job needs, taking it away when they leave, and finding out who changed
what. Every exercise is on the training shop, and every record it names is one the
training seed creates.

**About 1 hour**, in one sitting. **Before you start:** skim the
[role tracks](../index.md): you'll be choosing between them.

!!! warning "On a training instance only"
    Every exercise writes real records: a user you create can log in. See the
    [training program](../index.md).

## How a session runs

1. **Watch.** Your trainer works the modules on the training instance, saying what
   they look at and why.
2. **Regenerate.** Your trainer puts every exhibit back as it was (below).
3. **Do it with help.** You work the same modules on the same exhibits, with your
   trainer beside you.
4. **Alone.** After another regenerate, the [final task](#final-task-observed),
   with your trainer watching and not helping.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a Tenant Admin login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Alex Demo**, Tenant Admin, `admin@demo.ambac.com` | Every module |

The password is `demo123`.

---

## 1. Your desk

**You will:** find the admin pages.

Log in as Alex. Home shows every role's blocks at once: what needs attention,
quality, jobs going late, the inspection queue, approvals in flight, and the docks.
That's a Tenant Admin seeing everything, not a job to do all of it.

The **Admin** section of the sidebar holds **Settings**, **User Management**, **Data
Management** and **Audit Log**.

---

## 2. Add a user

**You will:** give a new operator a login.

1. **User Management** > **Add user**. Username (the login, usually their email),
   first and last name, email.
2. **Role**: tick **Operator**. A role is what the person can do in the app; tick
   more than one when someone covers two jobs (`Casey Cross` is QA Inspector and
   Shift Lead).
3. **Position**: **Assembler**. Position is separate from role: it's the job they
   hold, and it decides which competencies the training matrix expects of them.
4. Leave **Company** and **Contact for** empty: those are for people at a customer
   or supplier. **Create User**.

The new user is listed as *Never signed in*. **Send invitation** or **Copy access
link** on their row gives them a way in; from then until they accept, they're
listed as *Pending invite*.

---

## 3. Change what someone can do

**You will:** correct a role.

Open the user > **Edit**. Untick the role that's wrong, tick the right one, and
**Save Changes**: *User updated successfully!*

Every change to a user is on their edit page: field changes under **History**, role
changes and suspensions under **Access changes**. All of them are also in the audit
log (module 5).

---

## 4. Someone leaves

**You will:** suspend a user.

Open the user > **Edit**, untick **Active User** (*Uncheck this instead of deleting
accounts*), and **Save Changes**.

They can no longer log in. Their name stays on every record they signed, and they
can be reactivated. Users are never deleted: the record of who did the work is
evidence.

---

## 5. Who changed what

**You will:** read the audit log.

**Audit Log** lists every change made through the app, newest first: when, who, what
action, which record, and the fields before and after. Your last few minutes are
there: the user created, the role removed and added, *Is Active: True → False*.

**Settings** > **Roles & Permissions** lists the role groups, how many people are in
each and how many permissions each holds. **View** on one shows exactly what it can
do.

---

## What isn't yours

| Not yours | Whose |
|-----------|-------|
| Decide whether a person is competent for a step | QA manager (training records) |
| Approve a routing, a CAPA or a document | The approver its template names |
| Change a routing or a measurement | Engineering, under change control |

Your permissions let you write training records and change routings, which doesn't
make those calls yours. Approvals you can't make at all unless an approval template
names your group.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Alex, and says only: *"Jamie Ortiz
starts Monday as an inspector who'll also cover the shift lead. And Dave Wilson has
left."* Then they watch without helping:

- create Jamie with both roles and a position
- suspend Dave, without deleting him
- show in the audit log what you just did

Your trainer is watching for:

- [ ] Jamie has exactly the two roles asked for, and a position.
- [ ] Dave is inactive, not deleted.
- [ ] You found your own changes in the audit log.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
