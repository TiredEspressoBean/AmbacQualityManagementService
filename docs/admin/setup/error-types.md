# Error Types

Configure defect and non-conformance categories for quality tracking.

## What are Error Types?

Error Types categorize defects for:

- **Classification** - What kind of problem
- **Analysis** - Pareto and trending
- **Routing** - Different handling by type
- **Reporting** - Consistent categorization

## Suggested starting categories

**A new organisation has no error types — you create all of them.** Nothing is
seeded, so an empty list is the expected state rather than a sign something went
wrong. (A demo tenant is the exception: it carries defect types for its own
example parts.)

There is no category field on an error type, so the list below is a prompt for
what to create and what to call it, not a set of options to pick from:

| Type | Description |
|------|-------------|
| **Dimensional** | Out of tolerance, wrong size |
| **Visual/Cosmetic** | Scratches, dents, finish issues |
| **Material** | Wrong material, contamination |
| **Functional** | Doesn't work, fails test |
| **Documentation** | Missing/wrong paperwork |
| **Process** | Wrong operation, sequence error |
| **Supplier** | Incoming material defect |
| **Packaging** | Shipping/packaging damage |

## Creating Error Types

1. Navigate to **Data Management** > **Error Types**
2. Click **New Error Types**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Error Name** | Error type name | Yes |
| **Error Example** | A concrete example of the defect, so inspectors pick consistently | Yes |
| **Part Type** | Scope this error type to one part type, or leave blank for all | No |
| **Requires 3D Annotation** | The defect must be marked on the part's 3D model | No |

Submit with **Create Error Type**.

!!! tip "Requires 3D Annotation"
    Error types with this set appear in the **Part Annotator**, where the
    inspector marks the defect location on the model. Use it for defects whose
    position matters — see [Annotations](../../3d-models/annotations.md).

4. Save

## Error Type Hierarchy

!!! note "Not supported"
    Error types are a flat list. There is no parent field and no rollup
    reporting across a hierarchy.

    To get similar grouping, name types consistently (for example
    "Dimensional - Over Size", "Dimensional - Under Size") so they sort
    together, or scope them to a **part type** so inspectors only see the ones
    relevant to what they are working on.

## Error Type Fields

| Field | Required | Description |
|-------|:--------:|-------------|
| **Error Name** | Yes | Display name |
| **Error Example** | Yes | A concrete example of the defect |
| **Part Type** | No | Restricts the type to one part type |
| **Requires 3D Annotation** | No | Defect must be marked on the 3D model |

There is no code, description, parent, severity, colour, or icon field.

## Error Type Rules

Configure automatic behavior:

### Default Severity
!!! note "Planned Feature"
    Error types carry no rules of their own — no default severity, no
    auto-quarantine, and no automatic CAPA trigger.

    Severity is set on the **quality report** and the **CAPA** when they are
    raised. Quarantine follows from the quality report rather than from the
    error type. A CAPA is raised deliberately, not by a threshold rule.

## Reporting and Analysis

Error types drive analysis:

### Pareto Charts
- Defects grouped by type
- 80/20 analysis
- Prioritization

### Trend Analysis
- Error types over time
- Identify increasing issues
- Track improvement

### Heat Maps
- Defects by location and type
- Visual patterns

## Bulk import and export

Error types can be imported and exported. **Do not build the file from a column
list written here** — start at
[Data Management](../data/data-management.md), which carries the Import and
Export links for the defect catalogue, and export first to get the real header.

!!! warning "Older examples showed a hierarchy that does not exist"
    An earlier version of this page demonstrated a CSV with `code`,
    `description` and `parent_code` columns. None of those are fields. Error
    types are a flat list with the fields above, and the naming convention in
    *Grouping without a hierarchy* is how you get the grouping effect.

See [Import & Export](../data/import-export.md).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_qualityerrorslist` | View error types |
| `add_qualityerrorslist` | Create error types |
| `change_qualityerrorslist` | Edit error types |
| `delete_qualityerrorslist` | Deactivate error types |

## Next Steps

- [Quality Reports](../../workflows/quality/quality-reports.md) - Using error types
- [Defect Analysis](../../analysis/defects.md) - Analyzing data
- [CAPA](../../workflows/capa/overview.md) - Corrective actions
