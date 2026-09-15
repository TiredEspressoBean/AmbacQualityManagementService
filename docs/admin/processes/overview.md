# Process Overview

Processes define manufacturing workflows in uqmes. This guide explains process concepts and structure.

## What is a Process?

A **Process** is a defined sequence of steps for manufacturing a part type:

```
Raw Material → Machining → Inspection → Assembly → Final QA → Complete
```

Processes determine:
- What steps parts go through
- What's required at each step
- Quality control points
- Measurement requirements

## Process Structure

```
Process
  └── Step 1: Raw Material
        └── Requirements (none)
  └── Step 2: Machining
        └── Equipment: CNC Mill
        └── Work Instructions: WI-001
  └── Step 3: Inspection
        └── Measurements: Diameter, Length
        └── Sampling: AQL 2.5
  └── Step 4: Assembly
        └── Requirements: Training X
  └── Step 5: Final QA
        └── Measurements: All dimensions
        └── Approval: QA sign-off
  └── Step 6: Complete
```

## Process Types

### Production Process
Standard manufacturing workflow:
- Sequential steps
- Quality gates
- Measurement collection

### Rework Process
For correcting defects:
- Subset of production steps
- Additional inspection
- Links back to main process

### Incoming Inspection
For receiving material:
- Inspection steps only
- Sampling rules
- Supplier quality tracking

## Process Versioning

Processes support version control:

| Version | Status | Description |
|---------|--------|-------------|
| v1.0 | Obsolete | Original process |
| v2.0 | Obsolete | Added inspection step |
| v3.0 | Current | Updated measurements |
| v3.1 | Draft | Adding new equipment |

### Version Rules
- Only one **Current** version active
- **Draft** versions for development
- **Obsolete** versions archived
- Parts track which version they used

## Process Approval

Changes to processes may require approval:

1. Create or edit process (Draft)
2. Submit for approval
3. Reviewers approve changes
4. Process becomes Current
5. Previous version becomes Obsolete

## Linking Processes

### To Part Types
Each part type links to a default process:
- New parts of that type use the process
- Can override per work order

### To Work Orders
Work orders specify which process to follow:
- Usually default from part type
- Can select different process

## Process Configuration Elements

### Steps
Individual operations in sequence.

See [Step Configuration](steps.md).

### Measurements
Data collection requirements per step.

See [Measurement Definitions](measurements.md).

### Requirements
What's needed to complete a step:
- Training requirements
- Equipment requirements
- Document requirements
- Approval requirements

### Branching
Conditional paths through a process, built on the
[Process Flow](#process-flow) graph:

- **Decision points** — a step marked *Decision point* branches on its outcome
  (for example Pass / Fail)
- **Alternative routes** — rework and scrap paths off a failed decision
- **Terminal steps** — where a route ends, with its terminal status

## Viewing Processes

### Process List

Navigate to **Production** > **Processes**

See all processes with:
- Name and description
- Version and status
- Part types using it
- Step count

### Process Detail

Click a process to see:
- Full step sequence
- Each step's requirements
- Linked part types
- Version history

### Process Flow

**Process Flow** (`/process-flow`) is the editor for a process's steps and
routing — not an optional extra view:

- The routing as a flowchart, including branches and decision points
- **Edit Mode** to add, connect, and delete steps
- A properties panel per step (name, operation number, work center, timing)
  with an **Advanced** section for its gates
- A **Substeps** control opening that step's work instructions

See [Step Configuration](steps.md).

## Process Metrics

Track process performance:

| Metric | Description |
|--------|-------------|
| **Cycle Time** | Average time through process |
| **Step Duration** | Time at each step |
| **Bottleneck** | Longest step |
| **FPY** | First pass yield |
| **Rework Rate** | % requiring rework |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_processes` | View processes |
| `add_processes` | Create processes |
| `change_processes` | Edit processes |
| `respond_to_approval` | Respond to a process approval request (eligibility also set by the approval template) |
| `delete_processes` | Remove processes |

## Best Practices

1. **Match reality** - Process should reflect actual workflow
2. **Clear step names** - Unambiguous operations
3. **Appropriate detail** - Not too granular, not too broad
4. **Review regularly** - Update as operations change
5. **Version carefully** - Track changes properly

## Next Steps

- [Creating Processes](creating.md) - Build new processes
- [Step Configuration](steps.md) - Configure steps
- [Measurement Definitions](measurements.md) - Define measurements
