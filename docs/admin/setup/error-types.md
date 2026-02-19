# Error Types

Configure defect and non-conformance categories for quality tracking.

## What are Error Types?

Error Types categorize defects for:

- **Classification** - What kind of problem
- **Analysis** - Pareto and trending
- **Routing** - Different handling by type
- **Reporting** - Consistent categorization

## Default Error Types

Common categories:

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
2. Click **+ New Error Type**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Error type name | Yes |
| **Code** | Short code (DIM, VIS) | Yes |
| **Description** | Detailed description | No |
| **Category** | Parent category | No |
| **Active** | Available for selection | Yes |

4. Save

## Error Type Hierarchy

Organize in hierarchy:

```
Dimensional
├── Over Size
├── Under Size
├── Out of Position
└── Wrong Angle

Visual
├── Scratch
├── Dent
├── Discoloration
└── Surface Finish
```

Benefits:
- Detailed tracking
- Rollup reporting
- Easier selection

### Creating Hierarchy

1. Create parent error type (e.g., "Dimensional")
2. Create child types
3. Set **Parent** field to parent type
4. Save

## Error Type Fields

### Required

| Field | Description |
|-------|-------------|
| **Name** | Display name |
| **Code** | Short identifier |

### Optional

| Field | Description |
|-------|-------------|
| **Description** | Detailed definition |
| **Parent** | Parent category |
| **Default Severity** | Suggested severity |
| **Requires CAPA** | Auto-trigger CAPA |
| **Color** | Display color |
| **Icon** | Visual identifier |

## Error Type Rules

Configure automatic behavior:

### Default Severity
Pre-set severity for this type:
- Minor (cosmetic issues)
- Major (functional issues)
- Critical (safety/regulatory)

### Auto-Quarantine
Automatically quarantine parts:
- When this error type selected
- No manual step needed

### CAPA Trigger
Automatically create CAPA:
- After N occurrences
- For specific severity
- Based on rules

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

## Usage Guidelines

Document when to use each type:

```markdown
## Dimensional (DIM)
Use when measurement is out of specified tolerance.
Examples:
- Diameter too large/small
- Length out of spec
- Hole position off

DO NOT use for:
- Cosmetic issues (use Visual)
- Material hardness (use Material)
```

## Inactive vs Delete

- **Inactive**: Hides from selection, preserves history
- **Delete**: Not recommended, use inactive

Historical NCRs reference error types—don't break those links.

## Bulk Operations

### Import Error Types
```csv
code,name,description,parent_code
DIM,Dimensional,Measurement out of tolerance,
DIM-OS,Over Size,Larger than specified,DIM
DIM-US,Under Size,Smaller than specified,DIM
```

### Export
1. Click **Export**
2. Download CSV
3. Use for documentation or import

## Permissions

| Permission | Allows |
|------------|--------|
| `view_errortype` | View error types |
| `add_errortype` | Create error types |
| `change_errortype` | Edit error types |
| `delete_errortype` | Deactivate error types |

## Best Practices

1. **Keep it simple** - Start with major categories
2. **Add detail gradually** - Expand as needed
3. **Consistent definitions** - Clear when to use
4. **Train users** - Everyone uses same categories
5. **Review periodically** - Adjust based on use

## Next Steps

- [Quality Reports](../../workflows/quality/quality-reports.md) - Using error types
- [Defect Analysis](../../analysis/defects.md) - Analyzing data
- [CAPA](../../workflows/capa/overview.md) - Corrective actions
