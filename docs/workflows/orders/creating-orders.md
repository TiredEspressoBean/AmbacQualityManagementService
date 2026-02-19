# Creating Orders

Orders represent customer requests to manufacture or process parts. This guide covers creating and configuring orders.

## Before You Start

Ensure you have:

- Permission to create orders
- Customer records configured in the system
- Part types defined for the products you'll manufacture

## Creating a New Order

1. Navigate to **Data Management** > **Orders**
2. Click **+ New Order** in the top right
3. Complete the order form

### Required Fields

| Field | Description | Tips |
|-------|-------------|------|
| **Order Number** | Unique identifier | Use your PO/SO number format |
| **Customer** | Company placing the order | Select from dropdown |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Due Date** | Target completion date |
| **Priority** | Normal, High, or Rush |
| **Notes** | Internal comments |
| **Customer PO** | Customer's purchase order reference |
| **Ship To** | Delivery address if different from customer |

4. Click **Save**

## Order Numbering

Order numbers must be unique within your organization. Common formats:

- `PO-2026-0001` - Year-based sequential
- `SO-12345` - Simple sequential
- `CUST-ORD-001` - Customer prefix

!!! tip "Auto-Numbering"
    Your administrator may configure automatic order numbering. If so, the order number field may be pre-filled or read-only.

## Order Status

New orders start in **Draft** status. Status progresses as work is performed:

| Status | Meaning |
|--------|---------|
| **Draft** | Order created, not yet in production |
| **In Progress** | Work has begun, parts are being processed |
| **On Hold** | Order paused (quality issue, customer request) |
| **Complete** | All parts finished |
| **Shipped** | Order delivered to customer |
| **Cancelled** | Order cancelled |

## Linking to Work Orders

Orders need work orders to track production:

1. After creating the order, click **+ Add Work Order** or navigate to Work Orders
2. Select your order
3. Choose the process to apply
4. The work order links parts to the manufacturing workflow

See [Work Order Basics](../work-orders/basics.md) for details.

## Copying Orders

To create a similar order:

1. Open an existing order
2. Click **Duplicate** (or use the action menu)
3. Modify the copied order as needed
4. Save with a new order number

## Bulk Order Import

For creating multiple orders:

1. Navigate to **Data Management** > **Orders**
2. Click **Import**
3. Download the CSV template
4. Fill in order data
5. Upload the completed file

The system validates the import and reports any errors.

## Order Permissions

| Action | Required Permission |
|--------|---------------------|
| View orders | `view_orders` |
| Create orders | `add_orders` |
| Edit orders | `change_orders` |
| Delete orders | `delete_orders` |

Customer users can only view orders assigned to their company.

## Next Steps

- [Adding Parts](adding-parts.md) - Add parts to your order
- [Order Status](order-status.md) - Track order progress
- [Work Order Basics](../work-orders/basics.md) - Assign manufacturing processes
