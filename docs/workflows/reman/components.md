# Managing Harvested Components

This guide covers viewing and managing components extracted during core disassembly.

## Viewing Components

### From a Core

1. Open a core from **Reman > Cores**
2. Scroll to **Harvested Components** section
3. View all components from that core

### All Components

1. Navigate to **Reman > Components**
2. View all harvested components across cores
3. Use filters to narrow results

## Component Information

Each component displays:

| Field | Description |
|-------|-------------|
| **Component Type** | Type of component |
| **Core** | Source core it came from |
| **Condition Grade** | A, B, C, or Scrap |
| **Position** | Location within core |
| **Status** | In Inventory, Pending, or Scrapped |
| **Part ID** | Linked part if accepted to inventory |
| **Harvested Date** | When extracted |
| **Harvested By** | Who extracted it |

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

### Scrap

Marks a component as unusable:

1. Click **Scrap**
2. Enter scrap reason (required)
3. Component marked with scrap timestamp

### View Linked Part

For components in inventory:

1. Click the **Part ID** link
2. Opens the Parts detail page
3. View production history, location, etc.

## Filtering Components

Filter by:

- **Core** - Components from specific core
- **Component Type** - Specific part types
- **Condition Grade** - A, B, C, or Scrap
- **Status** - Pending, In Inventory, Scrapped
- **Date Range** - Harvested date

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

## Best Practices

1. **Disposition promptly** - Don't leave components pending long
2. **Document scrap reasons** - Helps identify recurring issues
3. **Verify condition** - Double-check grades before accepting
4. **Track yield** - Compare to expected fallout rates
5. **Review traceability** - Ensure links are maintained

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
