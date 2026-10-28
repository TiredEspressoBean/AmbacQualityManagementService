# Training Matrix

**Operator competency across training types** — who can do what, where the gaps
are, and which skills are a staffing risk.

**Quality** > **Training** > **Training Matrix** (`/quality/training/matrix`)

## Reading the matrix

People are rows, training types are columns. Each cell shows that person's
**current level** — the highest level they hold that is still in date.

| Marker | Meaning |
|--------|---------|
| **Red edge on a cell** | The skill is below that person's role requirement |
| **"N gaps" against a person** | How many required skills they're short |
| **"meets"** | That person satisfies their role's requirements |

The footer shows **how many people can cover each skill**.

## The four headline numbers

| Metric | Why it matters |
|--------|----------------|
| **People** | How many people are in scope |
| **People with role gaps** | Someone is assigned a role they aren't fully qualified for |
| **Skills at coverage risk** | One person can do it — or nobody can |
| **Expiring soon** | Qualifications about to lapse |

!!! warning "Thin coverage is a staffing risk"
    The tile counts every skill with one qualified person or none, so a skill
    nobody holds is in the same number as a skill one person holds. Either way
    that work stops — read the matrix itself to see which case each skill is.
    The matrix surfaces this deliberately — it's the number worth acting on
    before it becomes urgent.

## Why it affects scheduling

Training isn't only a compliance record. Operator dispatch will only assign
someone a step they are **qualified for at the required level**, so missing
competency becomes unassignable work on the schedule.

If the scheduler can't place work on a person you expected, check here first.
See [Schedule (Gantt)](../scheduling/gantt.md#dispatch).

!!! important "A role gap is not the same as being blocked from work"
    This is the commonest misreading of the matrix, and it goes both ways.

    A training requirement is scoped to **one** of: a **job role**, a **step**,
    a **process**, or an **equipment type**. The matrix reports **role fit** —
    whether someone meets the competence profile of the role they hold. The
    **start gate** reads **step** and **process** requirements.

    They are different questions:

    - Somebody can show **"1 gap"** here and still start **every step** they are
      asked to run, because no step or process they run required the skill they
      are short of. That is correct, not a bug.
    - Somebody can show **"meets"** and still be refused at a step, because that
      step or its process carries a requirement their role profile never
      mentioned.

    So read a role gap as *this person does not yet fit their job description* —
    a development and staffing signal — and the refusal at a step as *this
    person cannot run this operation today*. Only the second stops work.

## Filtering

Filter by role or search by name. **Highlight Level 1–2** picks out trainees
and assisted operators; **Expiry lens** picks out qualifications expiring or
expired.

## Next Steps

- **[Schedule (Gantt)](../scheduling/gantt.md)** - How qualification drives dispatch
- **[QA Manager Guide](../../roles/qa-manager.md)** - Training oversight
