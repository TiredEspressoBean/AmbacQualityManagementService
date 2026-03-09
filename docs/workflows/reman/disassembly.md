# Core Disassembly

This guide covers the process of disassembling cores to harvest reusable components.

## Prerequisites

Before starting disassembly:

- Core must have status `RECEIVED`
- User needs `change_core` and `add_harvestedcomponent` permissions
- Know what components to expect (see Disassembly BOM)

## Starting Disassembly

### Step 1: Open the Core

1. Navigate to **Reman > Cores**
2. Find and click on the core to disassemble
3. Review core information and condition notes

### Step 2: Start Disassembly

1. Click **Start Disassembly** button
2. Core status changes to `IN_DISASSEMBLY`
3. Disassembly start time is recorded

## Harvesting Components

As you extract each component:

### Step 1: Add Component

1. On the disassembly page, click **Add Component**
2. Select the **Component Type** from part types
3. Optionally enter:
   - **Position** - Location within core (e.g., "Cyl 1", "Position A")
   - **Original Part Number** - If readable from component

### Step 2: Assess Condition

Assign a condition grade:

| Grade | Criteria | Action |
|-------|----------|--------|
| **A** | Excellent - Ready for immediate reuse | Accept to inventory |
| **B** | Good - May need minor refurbishment | Accept to inventory |
| **C** | Fair - Needs significant work | Accept or scrap |
| **Scrap** | Not usable | Mark as scrapped |

Add condition notes for anything notable.

### Step 3: Save Component

Click **Save** to record the harvested component.

### Repeat for Each Component

Continue adding components until all usable parts are extracted.

## Component Disposition

After harvesting, each component needs disposition:

### Accept to Inventory

For usable components:

1. Click **Accept to Inventory** on the component
2. System creates a Parts record
3. Component is now available for production
4. Life tracking transfers from core (if applicable)

The created part receives an ERP ID like: `HC-[CoreNumber]-[TypePrefix][ID]`

### Scrap Component

For unusable components:

1. Click **Scrap** on the component
2. Enter scrap reason
3. Component is marked as scrapped

## Completing Disassembly

When all components are harvested:

1. Click **Complete Disassembly**
2. Core status changes to `DISASSEMBLED`
3. Completion time and user are recorded

## Scrapping a Core

If the core cannot be disassembled (too damaged, contaminated, etc.):

1. From the core detail page, click **Scrap**
2. Enter reason for scrapping
3. Core status changes to `SCRAPPED`
4. Condition grade set to `Scrap`

## Disassembly BOM

The Disassembly BOM shows expected components:

| Field | Description |
|-------|-------------|
| **Component Type** | Type of component expected |
| **Expected Qty** | Number expected per core |
| **Fallout Rate** | Percentage typically unusable |

Use this as a checklist during disassembly to ensure all components are accounted for.

## Life Tracking Transfer

When a component is accepted to inventory:

- Life tracking records from the core are examined
- Records applicable to the component type are transferred
- Source is marked as `TRANSFERRED`
- Maintains traceability of accumulated life

## Best Practices

1. **Follow the BOM** - Use as a checklist
2. **Grade consistently** - Apply same standards to all components
3. **Document damage** - Note any issues found
4. **Handle carefully** - Prevent damage during extraction
5. **Clean workspace** - Keep components organized
6. **Complete promptly** - Don't leave cores partially disassembled

## Troubleshooting

### Cannot Start Disassembly

- Verify core status is `RECEIVED`
- Check you have required permissions
- Ensure core is not already in disassembly

### Component Type Not Found

- Component types come from Part Types
- Ask administrator to add the part type
- Use a similar type temporarily if urgent

### Life Tracking Not Transferring

- Life tracking only transfers if component type has PartTypeLifeLimit
- Check that life definitions apply to this component type

## Next Steps

- [Managing Components](components.md) - View and manage harvested components
- [Issue Core Credit](overview.md#core-credit) - Process customer credits
