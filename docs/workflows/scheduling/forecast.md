# Volume Forecast

**The new builds you expect, by part type and month — what the two-year outlook
plans beyond firm orders.**

`/production/forecast` — from **Data Management** (**Equipment & scheduling** >
**Volume Forecast**), or from the forecast line on [Capacity
Planning](capacity.md). It is not in the sidebar: it is revised about once a
month, not worked daily.

## The grid

Part types run down the side and **24 months** across, starting from the
current month. Type a quantity in a cell; it saves when you leave the cell or
press **Enter**. A blank or **0** clears that month. **Add a part type…** adds a
row.

Under each cell, *&lt;N&gt; ordered* is what orders due that month already claim
of the forecast — firm orders and RFIs together. It turns green once orders
cover the whole forecast. Hover a cell for the breakdown: the forecast, *Firm
orders* and *RFI*, and *Planned on top of orders*.

## Orders use up the forecast

A forecast is expected volume, and the orders you win are part of it — not
extra on top. So in each month:

- Firm orders and RFI deals due that month **use up** that month's forecast.
- The month plans the larger of the forecast and what orders already claim.
  Only the **unclaimed rest** adds load.
- That rest is placed as if due at the month's end, the same way an [open order
  line](capacity.md#whats-in-the-load) is placed back from its due date.

What counts as claiming it: order lines that aren't cancelled, at their full
quantity, plus work orders that aren't on any order line. A work order on an
order line is that line's own units, not counted twice. Teardown and
disassembly work claims nothing: the forecast covers new builds only.

## Importing a forecast

**Import forecast** takes a sheet with three columns:

| Column | Holds |
|--------|-------|
| **Item** | The part type's ERP id, or its exact name |
| **Month** | `YYYY-MM` — `3/2027`, `Mar 2027`, `March-27`, or any date in the month, are read too |
| **Quantity** | Units expected that month |

- Each row **replaces** the month it names; months not on the sheet keep their
  values.
- **0** or blank clears the month.
- Rows that can't be read are listed, and the rest still land.

**Template (.csv)** in the dialog downloads an empty sheet with the columns.

## Permissions

| Permission | Allows | Held by default |
|------------|--------|-----------------|
| `view_volumeforecast` | See the forecast | Every staff role |
| `add_volumeforecast`, `change_volumeforecast` | Edit cells and import | Planner, Production Manager, Tenant Admin |

Without the edit permissions the numbers are read-only. Clearing a cell
archives the month rather than deleting it.

## Related

- [Capacity Planning](capacity.md) — where the forecast's load shows
- [Order Status](../orders/order-status.md) — RFI orders count as tentative
