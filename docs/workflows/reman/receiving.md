# Receiving Cores

This guide covers how to receive and log incoming cores for remanufacturing.

## When to Receive a Core

Receive a core when:

- Customer returns a used unit
- Purchasing receives cores from suppliers
- Warranty returns arrive
- Trade-in units are collected

## Receiving Workflow

### Step 1: Open the receiving form

Go to `/reman/cores/receive` for the **Receive Core** form.

!!! warning "Don't use New Cores"
    **Remanufacturing > Cores** is a record list with a generic **New Cores**
    create button. It will make a core record, but it is not the receiving
    form — use **Receive Core**, which captures source type, condition grade,
    and credit value together.

    For a delivery of several cores at once, use
    `/reman/cores/receive-batch`.

### Step 2: Enter Core Information

**Required Fields:**

| Field | Description |
|-------|-------------|
| **Core Number** | Unique identifier for this core |
| **Core Type** | Type of unit (select from part types) |
| **Source Type** | How the core was obtained, e.g. Customer Return |
| **Received Date** | Date the core was received |
| **Condition Grade** | Overall condition, e.g. Grade B - Good |

**Optional Fields:**

| Field | Description |
|-------|-------------|
| **Serial Number** | Original equipment serial number |
| **Reference Number** | RMA, PO, or other reference |
| **Customer** | Customer who returned the core |
| **Credit Value ($)** | Core credit owed for the return |
| **Condition Notes** | Detailed observations |

Submit with **Receive Core**.
| **Core Credit Value** | Credit amount owed for return |

### Step 3: Assess Condition

Assign a condition grade based on inspection:

| Grade | Condition | Typical Action |
|-------|-----------|----------------|
| **A** | Excellent - Minimal wear | High-value disassembly |
| **B** | Good - Normal wear | Standard disassembly |
| **C** | Fair - Significant wear | Selective component harvest |
| **Scrap** | Not usable | Scrap entire core |

!!! tip "Condition Notes"
    Document specific observations: visible damage, missing components, corrosion, etc. These notes help during disassembly.

### Step 4: Set Core Credit (if applicable)

For customer returns with credit agreements:

1. Enter the **Core Credit Value**
2. Credit can be issued later after processing
3. Credit issuance is timestamped for accounting

### Step 5: Save Core

Click **Save** to create the core record. The core status will be `RECEIVED`.

## Source Types

| Source | Use When |
|--------|----------|
| **Customer Return** | Customer returns core as part of reman exchange |
| **Purchased** | Core purchased from supplier or broker |
| **Warranty** | Core returned under warranty claim |
| **Trade-In** | Core accepted as trade-in on new purchase |

## After Receiving

Once received, cores can be:

1. **Disassembled** - Start extracting components
2. **Scrapped** - If inspection reveals core is not usable
3. **Held** - Awaiting decision or additional information

## Best Practices

1. **Inspect immediately** - Assess condition while receiving
2. **Document thoroughly** - Take photos, note damage
3. **Verify identity** - Confirm core matches paperwork
4. **Handle carefully** - Prevent additional damage
5. **Route appropriately** - Move to staging area

## Troubleshooting

### Core Number Already Exists

Core numbers must be unique. If the number is already used:

- Check if this is a duplicate receipt
- Use a different numbering scheme
- Append a suffix to distinguish

### Customer Not Found

If the returning customer isn't in the system:

- Add the company first via **Data Management > Companies**
- Or leave customer blank and add later

## Next Steps

- [Start Disassembly](disassembly.md) - Take apart the core
- [View Core Details](overview.md) - Review core information
