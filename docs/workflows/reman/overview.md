# Remanufacturing Overview

The Remanufacturing (Reman) module enables tracking of used units (cores) through disassembly to harvest reusable components.

## What is Remanufacturing?

Remanufacturing recovers value from used products by:

1. **Receiving Cores** - Accepting used units from customers, purchases, or returns
2. **Disassembly** - Taking apart cores to extract components
3. **Component Assessment** - Grading components for reusability
4. **Inventory Integration** - Adding usable components to production inventory

Common in automotive (engine blocks, transmissions), aerospace (turbine engines), and industrial equipment industries.

## Core Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   RECEIVED   │────▶│IN_DISASSEMBLY│────▶│ DISASSEMBLED │
│              │     │              │     │              │
│ Core logged  │     │ Being taken  │     │ Components   │
│ and graded   │     │ apart        │     │ harvested    │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       │ If not usable
       ▼
┌──────────────┐
│   SCRAPPED   │
│              │
│ Core deemed  │
│ unusable     │
└──────────────┘
```

## Key Concepts

### Cores

A **core** is a complete used unit received for remanufacturing:

- Has a unique core number
- Assigned a condition grade (A, B, C, or Scrap)
- Tracked from receipt through disassembly
- May have a core credit value for customer returns

### Harvested Components

**Harvested components** are parts extracted during disassembly:

- Each component is graded for condition
- Usable components can be accepted into inventory
- Creates full traceability back to source core
- Life tracking can transfer from core to component

### Disassembly BOM

The **Disassembly BOM** defines expected yields:

- Lists expected components per core type
- Includes expected fallout rates
- Helps plan component inventory

## Workflow Summary

### 1. Receive Core

When a core arrives:

1. Navigate to **Reman > Receive Core**
2. Enter core number and serial (if available)
3. Select core type
4. Assign condition grade
5. Record source (customer return, purchase, etc.)
6. Set core credit value if applicable
7. Save to create core record

### 2. Disassembly

To disassemble a core:

1. Open core from **Reman > Cores**
2. Click **Start Disassembly**
3. Add harvested components as you extract them
4. Grade each component's condition
5. Click **Complete Disassembly** when done

### 3. Component Disposition

For each harvested component:

- **Accept to Inventory** - Creates a Part record for reuse
- **Scrap** - Mark as unusable with reason

### 4. Core Credit

If core credit is owed:

1. Verify credit value is set
2. Click **Issue Credit**
3. Credit timestamp is recorded

## Permissions

| Permission | Allows |
|------------|--------|
| `view_core` | View cores |
| `add_core` | Receive new cores |
| `change_core` | Update core information |
| `delete_core` | Delete cores |
| `view_harvestedcomponent` | View harvested components |
| `add_harvestedcomponent` | Add components during disassembly |
| `change_harvestedcomponent` | Update component information |

## Related Topics

- [Receiving Cores](receiving.md) - Detailed receiving workflow
- [Disassembly Process](disassembly.md) - Step-by-step disassembly
- [Component Management](components.md) - Managing harvested components
