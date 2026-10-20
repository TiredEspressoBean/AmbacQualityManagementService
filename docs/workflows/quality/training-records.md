# Training Records

A training record says that a person completed a training, and at what level of
competency. Training requirements on a step read these records: someone without an
in-date record at the required level is refused when they start that step, and a
shift lead's override is the only way past.

So a record is operational, not clerical. A person who has been assessed and
signed off is still refused the work until their record exists.

## Record a training

**Quality** > **Training**, then **Record New Training**.

| Field | Set it to |
|-------|-----------|
| **Trainee** | The person who was assessed |
| **Training Type** | The qualification being awarded |
| **Completion Date** | The date of the assessment, not the day you enter it |
| **Competency Level** | The level the person actually demonstrated (below) |
| **Expiration Date** | Usually leave it empty. It is calculated from the training type's validity period; with no validity period, the record never expires |
| **Trainer** | Whoever conducted and assessed it |
| **Notes** | What was assessed and how, if your procedure asks for it |

### Competency levels

| Level | Means |
|-------|-------|
| **1 — Trainee** | Works supervised |
| **2 — Assisted** | Works alone, but the output is checked |
| **3 — Qualified** | Works independently |
| **4 — Expert** | Works independently, and can train and sign off others |

A step's training requirement names a minimum level. A person's level for a
training is the highest level among their in-date records for it.

!!! note "Level is an assessed result, not attendance"
    The competency level is the evidence of what the person can do (ISO 9001
    7.2). Recording everyone at the same level because they attended the course
    defeats the control, and the training matrix that supervisors plan from
    stops being true.

## See who is qualified

- **Training Matrix** (on **Quality** > **Training**): people against
  trainings, with each person's level and what is expiring.
- **Training Overrides** (on **Quality** > **Training**): every start
  a shift lead authorised for someone who wasn't qualified, with the reason. A
  person who keeps appearing here needs a record, not more overrides.
