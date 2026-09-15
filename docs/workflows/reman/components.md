# Managing Harvested Components

This guide covers viewing and managing components extracted during core disassembly.

## Viewing Components

### From a Core

1. Open a core from **Remanufacturing > Cores**
2. Scroll to **Harvested Components** section
3. View all components from that core

### All Components

1. Navigate to **Remanufacturing > Components**
2. View all harvested components across cores
3. Use filters to narrow results

## Component Information

Each component displays:

| Field | Description |
|-------|-------------|
| **Component Type** | Type of component |
| **Source Core** | The core it came from |
| **Position** | Location within the core |
| **Condition** | A, B, C, or Scrap |
| **Status** | In Inventory, Pending, or Scrapped |
| **Part ID** | Linked part, if accepted to inventory |
| **Harvested** | When it was extracted |
| **By** | Who extracted it |

## Component Statuses

| Status | Meaning |
|--------|---------|
| **Pending** | Harvested but not yet dispositioned |
| **In Inventory** | Accepted and has linked Parts record |
| **Scrapped** | Marked as unusable |

## Actions

### Accept to Inventory

Converts a pending component into inventory:

1. Click **Accept to Inventory**
2. System creates a Parts record
3. Component links to the new part
4. Life tracking transfers if applicable

The part can then enter production workflows.

### Scrapping

A component that cannot be used carries the **Scrapped** status. Scrapping is
decided during [disassembly](disassembly.md) when the component is graded,
rather than as an action on this list.

### View Linked Part

For components in inventory:

1. Click the **Part ID** link
2. Opens the Parts detail page
3. View production history, location, etc.

## Filtering Components

The list has a single control — a **search** box ("Search harvested
components...") — plus **Import** and **Export**.

!!! note "No filter dropdowns"
    There is no filtering by core, component type, condition, status, or
    date on this page. Use search, or export to CSV and slice it there.

## Traceability

Harvested components maintain full traceability:

```
Finished Product
      ↓
    Part (production history)
      ↓
Harvested Component
      ↓
    Core (source core)
      ↓
  Customer/Source
```

This chain enables:

- Warranty tracking back to source
- Quality issue investigation
- Life tracking continuity

## Inventory Integration

When a component is accepted to inventory:

1. **Parts Record Created**
   - ERP ID generated: `HC-[CoreNumber]-[Prefix][ID]`
   - Status: `PENDING`
   - Part type matches component type

2. **Life Tracking Transferred**
   - Applicable life records copied
   - Source marked as `TRANSFERRED`
   - Accumulated values preserved

3. **Ready for Production**
   - Part can be added to orders
   - Enters normal production tracking
   - Maintains link back to harvested component

## Reporting

### Component Yield Report

Track disassembly performance:

- Components harvested per core type
- Acceptance vs scrap rates
- Condition grade distribution
- Comparison to expected fallout rates

### Inventory Impact

- Components added to inventory over time
- Value recovered from cores
- Most common component types harvested

## Troubleshooting

### Cannot Accept to Inventory

- Component may already be accepted
- Component may be scrapped
- Check for required permissions

### Part Not Appearing

- Verify acceptance completed
- Check the Parts list with appropriate filters
- Look for the `HC-` prefix in ERP ID

### Life Tracking Missing

- Not all life definitions apply to all part types
- Check PartTypeLifeLimit configuration
- Life only transfers when definitions match

## Related Topics

- [Disassembly Process](disassembly.md) - How to harvest components
- [Parts Tracking](../tracking/tracker-overview.md) - Tracking accepted parts
- [Life Tracking](../tracking/life-tracking.md) - Component life management
