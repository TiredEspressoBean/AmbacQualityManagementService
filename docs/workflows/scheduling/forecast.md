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

Under each cell, *&lt;N&gt; ordered or planned* is everything due that month, in
full: firm and RFI order lines, plus stock builds (work orders on no order line).
It can be more than the forecast. It turns green once the month's forecast is all
used up. When some of it is beyond **every** forecast it could use up — this
month's and its neighbours' within the [consumption window](#settings) — it turns
amber and adds *· &lt;M&gt; over forecast*. An order a neighbouring month's
forecast covers isn't over.

Hover a cell for the breakdown, one line each:

- *Forecast &lt;F&gt;*
- *Ordered or planned this month: firm &lt;X&gt; (order lines and stock builds)
  · RFI &lt;Y&gt;*
- *&lt;M&gt; beyond every forecast within the consumption window* — only when
  some is over
- *Forecast used up by orders: firm &lt;A&gt; · RFI &lt;B&gt;* — whichever month
  the orders are due in, followed by *of which RFI 50 (from Mar 27)* for those
  due in a neighbouring month
- *Planned on top of orders: &lt;P&gt;*

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

Only this month and later take part. An order already past its due date uses up
no forecast — its work is in the load as overdue — and past months' forecast
drops out. A cell reads the same whichever months you look at.

Then each month:

- plans the larger of its forecast and what orders have used up — only the
  **unclaimed rest** adds load;
- places that rest as if due at the month's end, the same way an [open order
  line](capacity.md#whats-in-the-load) is placed back from its due date.

## The demand time fence

Close in, a forecast is not worth planning against — only real orders should
drive the next few weeks. Inside the **demand time fence**, counted in days
from today, the forecast is **shown but not planned**: capacity, the material
lane and the material outlook export count only firm and RFI orders there.

- A month **wholly** inside the fence is muted on this page — *"Inside the
  demand time fence: only orders are planned."* — and stays editable.
- A month the fence **straddles** plans only its days past the fence: its
  unclaimed forecast is pro-rated by days, counting from today (days already
  gone aren't fenced). Its tooltip says how much is held back — *Planned on top
  of orders: &lt;P&gt; — &lt;F&gt; of the &lt;U&gt; unclaimed fall inside the
  demand time fence (days before it are pro-rated out)*.

The fence moves with today, so it protects the same number of days whatever
the date — the default is the next 30.

## Settings

Both are in **Scheduling settings**, under **Time fences**, for whoever can
change scheduling settings:

| Setting | Default | Means |
|---------|---------|-------|
| **Demand time fence (days)** | 30 | *"Days from today in which forecast isn't planned — only orders count. A month straddling the fence plans only its days past it. 0 = off."* At most 365. |
| **Forecast consumption window (months)** | 1 | *"How far either side of its due month an order uses up forecast: earlier months first, then later. 0 = its due month only."* At most 12. |

What counts as claiming it: order lines that aren't cancelled or deleted, at
their full quantity, plus work orders that aren't on any order line. A work
order on an order line is that line's own units, not counted twice. The
forecast covers **new builds only**, so remanufacturing claims nothing:
teardown and remanufacture work orders, and order lines whose
[fulfilment](../orders/creating-orders.md#order-lines) is **Repair & return** or
**Exchange** — from the moment the line is entered, before any core arrives.

A forecast belongs to its part type: when the part type is revised to a new
version, its forecast moves with it. When the part type is archived, its
forecast stops loading and its row leaves the grid.

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
