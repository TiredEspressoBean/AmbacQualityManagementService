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

Accepting a component mints a **Parts** record for it, links the component to
that part, and transfers any applicable life tracking.

The new part is created **In Stock**, not Pending — available supply counts only
In Stock, so a recovered component left Pending would be invisible as supply and
a rebuild would go looking for one to buy while it sat on the shelf.

Both actions are on the row menu on the Harvested Components page. Accepting
opens a dialog that takes an **optional part ID** — one is generated if you
leave it blank — and tells you when the part will be reserved. Scrapping
requires a reason.

!!! info "Grading and deciding are separate jobs"
    Recording a component and its grade is the teardown technician's work.
    **Accepting** it into stock needs `accept_component`, and **scrapping** it
    needs `reject_component` — both enforced on the server, not just hidden in
    the UI. The person who tore the unit down does not decide what becomes of
    what they found.

!!! warning "An accepted part can be spoken for"
    If the component's core is going back to its customer, the part is
    **reserved to that core** and cannot go into anyone else's rebuild. The
    dialog says so before you accept.

### Scrapping

A component that cannot be used carries the **Scrapped** status. Grading it
Scrap at teardown is the usual route, but it can also be scrapped from the row
menu here — that needs `reject_component` and a reason.

### View Linked Part

For components in inventory:

1. Click the **Part ID** link
2. Opens the Parts detail page
3. View production history, location, etc.

## Findings: a component found worse at the bench

Teardown grades every component, and those grades resolve the rebuild — **A** and
**B** go back as they are, **C** is reconditioned, **Scrap** is replaced — with
each resolution raising the repair codes that make up the rebuild's scope.

Sometimes a component turns out worse later: a reused nozzle that fails its spray
test, a valve seat that looked fine until it was cleaned.

### Recording one

The rebuilder records it from the step player, as a **rebuild finding** capture.
That is all an operator does — recording a finding changes nothing on its own.

### Deciding one

A lead applies or dismisses each finding on the [rebuild plan](rebuild.md) page.
This needs the `accept_component` permission.

| Decision | Effect |
|----------|--------|
| **Apply** | The component is re-graded, and the rebuild plan re-resolves from the new grade exactly as it would have at teardown. Applying a **Scrap** grade also scraps the component outright |
| **Dismiss** | The grade stands. **A reason is required** |

A finding that proposes the grade a component already carries is refused — there
is nothing to decide.

Both outcomes are appended to the component's condition notes, and every grade
change is in the audit log. A component carries **one pending finding at a
time**.

!!! info "Why a person decides this"
    A finding changes the rebuild's scope — and on a repair-and-return unit,
    scope is the customer's bill. So the system separates the two acts
    deliberately: an operator *records* what they found, a lead *decides* what
    it means.

    It is kept human for now on purpose. Once there is data on how findings are
    actually decided, parts of it may be worth automating; until then the system
    records and a person decides.

!!! warning "Applying a finding does not contact the customer"
    Nothing here sends a unit for authorisation, and nothing here prices
    anything. Whether the new scope needs the customer's agreement is the lead's
    judgement, made separately — see the authorisation hold in
    [Teardown](disassembly.md).

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
   - Status: **In Stock** — see [Accept to Inventory](#accept-to-inventory)
   - Part type matches component type

2. **Life Tracking Transferred**
   - Applicable life records copied
   - Source marked as `TRANSFERRED`
   - Accumulated values preserved

3. **Ready for Production**
   - Part can be added to orders
   - Enters normal production tracking
   - Maintains link back to harvested component

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
