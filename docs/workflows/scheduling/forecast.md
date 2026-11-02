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

Under each cell, *&lt;N&gt; ordered* is how much of that month's forecast orders
have used up — firm orders and RFIs together, including orders due in a
neighbouring month (see below). It turns green once orders cover the whole
forecast. Hover a cell for the breakdown: the forecast, which orders used it up
and from which month — *of which Firm 10 (from Mar 27), RFI 60 (from Apr 27)* —
and *Planned on top of orders*.

## Orders use up the forecast

A forecast is expected volume, and the orders you win are part of it — not
extra on top. So an order uses up forecast, in this order:

1. its **due month**;
2. then **earlier** months, nearest first;
3. then **later** months —

within the **forecast consumption window** either side of the due month (see
[Settings](#settings)). That way an order due on 2 March isn't counted again
against February's forecast for the same build. Orders are taken in due-month
order, firm before RFI within a month, and a month's forecast never goes below
zero.

Then each month:

- plans the larger of its forecast and what orders have used up — only the
  **unclaimed rest** adds load;
- places that rest as if due at the month's end, the same way an [open order
  line](capacity.md#whats-in-the-load) is placed back from its due date.

## The demand time fence

Close in, a forecast is not worth planning against — only real orders should
drive the next few weeks. Inside the **demand time fence**, the forecast is
**shown but not planned**: capacity, the material lane and the material outlook
export count only firm and RFI orders there. Fenced month columns are muted on
this page — *"Inside the demand time fence: only orders are planned."* — and stay
editable. With the default of 1, the current month carries no forecast load.

## Settings

Both are in **Scheduling settings**, in the **Fences** group, for whoever can
change scheduling settings:

| Setting | Default | Means |
|---------|---------|-------|
| **Demand time fence (months)** | 1 | *"Months from now in which forecast isn't planned — only orders count. 1 = this month; 0 = off."* |
| **Forecast consumption window (months)** | 1 | *"How far either side of its due month an order uses up forecast: earlier months first, then later. 0 = its due month only."* |

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
