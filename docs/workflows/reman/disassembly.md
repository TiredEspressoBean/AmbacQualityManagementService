# Core Disassembly

This guide covers the process of disassembling cores to harvest reusable components.

## Prerequisites

Before starting disassembly:

- Core must have status `RECEIVED`
- User needs `change_core` and `add_harvestedcomponent` permissions
- Know what components to expect (see Disassembly BOM)

## Starting Disassembly

### Step 1: Open the Core

1. Navigate to **Remanufacturing > Cores**
2. Find and click on the core to disassemble
3. Review core information and condition notes

### Step 2: Start Disassembly

1. Click **Start Disassembly** button
2. Core status changes to `IN_DISASSEMBLY`
3. Disassembly start time is recorded

## Harvesting Components

As you extract each component:

### Step 1: Harvest the component

1. On the disassembly page, click **Harvest Component**
2. Fill in the dialog:

| Field | Required | Description |
|-------|:--------:|-------------|
| **Component Type** | Yes | Which component this is |
| **Condition Grade** | Yes | Its condition, e.g. *Grade B - Good* |
| **Position** | No | Location within the core, e.g. "Cyl 1" |
| **Original Part Number** | No | If readable from the component |
| **Condition Notes** | No | Anything notable |

### Step 2: Assess Condition

Assign a condition grade:

| Grade | Criteria | Action |
|-------|----------|--------|
| **A** | Excellent - Ready for immediate reuse | Accept to inventory |
| **B** | Good - May need minor refurbishment | Accept to inventory |
| **C** | Fair - Needs significant work | Accept or scrap |
| **Scrap** | Not usable | Mark as scrapped |

Add condition notes for anything notable.

### Step 3: Record it

Click **Harvest** to record the component.

### Repeat for Each Component

Continue harvesting until all usable parts are extracted, then click
**Complete Disassembly**.

## Component Disposition

After harvesting, each component needs disposition:

### Scrap during disassembly

A component you can see is unusable can be scrapped here — **Scrap** is
available on the disassembly page as you work through the core.

### Accept to Inventory

Accepting happens afterwards, from **Remanufacturing** > **Components**, not on
the disassembly page:

1. Open the component from the Harvested Components list
2. Click **Accept to Inventory**
3. The system creates a Parts record and links the component to it
4. Life tracking transfers from the core, if applicable

The created part receives an ERP ID of the form
`HC-{core number}-{type prefix}{id}`.

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
