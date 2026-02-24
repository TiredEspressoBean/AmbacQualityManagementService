# Production Manager Training Guide

**Duration:** 3-5 hours
**Prerequisites:** None
**Goal:** Learn to create orders, manage work orders, monitor production, and coordinate with quality

!!! note "Training Data Setup"
    Exercises reference sample data (e.g., "TRAIN-PM-001", "TRAIN-BOTTLE"). Your administrator should set up training data, or you can create your own test records following the exercise patterns.

---

## Module 1: Production Manager Role Overview

### Learning Objectives

By the end of this module, you will:

- [ ] Understand your production management responsibilities
- [ ] Navigate production-specific screens
- [ ] Understand the order-to-delivery flow

### 1.1 Your Role

As a Production Manager, you:

- Create and manage customer orders
- Create work orders and assign resources
- Monitor production progress
- Manage priorities
- Coordinate with quality on holds
- Track on-time delivery

---

### 1.2 Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Tracker** | Portal > Tracker | Order overview |
| **Orders** | Data Management > Orders | Order management |
| **Work Orders** | Production > Work Orders | Production assignments |
| **Analytics** | Tools > Analytics | Metrics |
| **Inbox** | Personal > Inbox | Alerts |

**Exercise 1.1:** Navigation Tour

1. Visit each page listed above
2. Note the key information on each
3. Identify where you'd create new items

---

### 1.3 Order-to-Delivery Flow

```
Customer PO → Create Order → Add Parts → Create Work Order →
Production → Quality → Ship → Complete
```

You manage the first half; operators and QA handle execution.

---

### Knowledge Check: Module 1

1. Where do you create new orders?
2. What is the difference between an Order and a Work Order?
3. Where do you see overall production progress?

---

## Module 2: Creating Orders

### Learning Objectives

By the end of this module, you will:

- [ ] Create orders with complete information
- [ ] Add parts to orders
- [ ] Import orders in bulk

### 2.1 Order Information

**Required fields:**

| Field | Description |
|-------|-------------|
| **Order Number** | Your PO/SO reference |
| **Customer** | Select from company list |
| **Due Date** | Target completion date |
| **Priority** | Normal, High, Rush |

**Optional fields:**

- Customer PO reference
- Notes/special instructions
- Project reference

---

### 2.2 Creating an Order

**Steps:**

1. Navigate to **Data Management** > **Orders**
2. Click **+ New Order**
3. Fill in required fields
4. Add notes if needed
5. Save

**Exercise 2.1:** Create an Order

1. Go to Orders
2. Create new order:
   - Order Number: "TRAIN-PM-001"
   - Customer: Select training customer
   - Due Date: 2 weeks from today
   - Priority: Normal
3. Save

---

### 2.3 Adding Parts

**After creating order:**

1. Open the order
2. Go to **Parts** section
3. Click **+ Add Parts**
4. Configure:
   - Part Type: Select product
   - Quantity: Number of parts
   - Serial Prefix: (optional) for serial numbers
   - Lot Number: (optional) for lot tracking
5. Add

**Exercise 2.2:** Add Parts

1. Open order "TRAIN-PM-001"
2. Add parts:
   - Part Type: Select training part type
   - Quantity: 10
   - Serial Prefix: "PM-001"
3. Verify parts created with serial numbers PM-001-001 through PM-001-010

---

### 2.4 Bulk Import

**For multiple orders:**

1. Click **Import**
2. Download CSV template
3. Fill in order data in spreadsheet
4. Upload CSV
5. Review and confirm

---

### Knowledge Check: Module 2

1. What are the required fields for an order?
2. How do you specify the number of parts?
3. What is the serial prefix used for?

---

## Module 3: Work Orders

### Learning Objectives

By the end of this module, you will:

- [ ] Create work orders
- [ ] Assign resources
- [ ] Set priorities

### 3.1 Work Order Purpose

**Work orders:**

- Link orders to manufacturing processes
- Assign equipment and resources
- Track production execution
- Enable scheduling

An order can have multiple work orders if needed.

---

### 3.2 Creating Work Orders

**Steps:**

1. Navigate to **Production** > **Work Orders**
2. Click **+ New Work Order**
3. Select:
   - Order (links to customer order)
   - Process (manufacturing process)
   - Priority
   - Due date
4. Optional: Assign equipment
5. Save

**Exercise 3.1:** Create Work Order

1. Go to Work Orders
2. Create new:
   - Order: "TRAIN-PM-001"
   - Process: Select training process
   - Priority: Normal
   - Due Date: Match order due date
3. Save

---

### 3.3 Work Order Settings

| Setting | Purpose |
|---------|---------|
| **Priority** | Affects queue position |
| **Notes** | Special instructions for floor |

!!! note "Equipment Assignment"
    Equipment assignment to work orders is planned for a future release. Currently, equipment is tracked at the process step level through step execution records.

---

### 3.4 Priority Levels

| Level | When to Use |
|-------|-------------|
| **Rush** | Emergency, expedite immediately |
| **High** | Important customer, tight deadline |
| **Normal** | Standard production |

**Changing priority:**

1. Open work order
2. Change priority field
3. Save
4. Communicate to floor if urgent

---

### Knowledge Check: Module 3

1. What does a work order link together?
2. When would you set priority to "Rush"?
3. How do you assign a work order to specific equipment?

---

## Module 4: Monitoring Production

### Learning Objectives

By the end of this module, you will:

- [ ] Track order progress
- [ ] Identify bottlenecks
- [ ] Use the dashboard effectively

### 4.1 Tracker Page

**What you see:**

- Order cards with progress bars
- Color coding for on-time status
- Expandable details
- Search and filters

**Progress colors:**

| Color | Meaning |
|-------|---------|
| Green | On track |
| Yellow | At risk |
| Red | Behind schedule |

**Exercise 4.1:** Review Production Status

1. Go to Tracker
2. Identify any red (behind) orders
3. Expand an order to see part details
4. Note which steps parts are at

---

### 4.2 Step Distribution

**Expanding an order shows:**

- Parts at each step
- Step completion counts
- Who's working on what

Use this to identify:

- Bottleneck steps (many parts waiting)
- Idle steps (nothing in queue)
- Progress flow issues

---

### 4.3 Identifying Problems

**Signs of trouble:**

- Parts stuck at one step
- No movement in 24+ hours
- Growing WIP at a step
- Quality holds blocking progress

**Exercise 4.2:** Find Bottlenecks

1. Expand order "TRAIN-BOTTLE"
2. Identify which step has most parts waiting
3. Note how long parts have been there

---

### 4.4 Analytics Dashboard

**Key metrics to monitor:**

- On-time delivery rate
- Throughput by area
- WIP levels
- Cycle time trends

Navigate to **Analytics** for detailed views.

---

### Knowledge Check: Module 4

1. What does a red progress bar indicate?
2. How do you identify a bottleneck step?
3. Where do you find detailed production metrics?

---

## Module 5: Handling Quality Issues

### Learning Objectives

By the end of this module, you will:

- [ ] Respond to quality holds
- [ ] Coordinate with QA
- [ ] Update schedules appropriately

### 5.1 Quality Alerts

**You'll be notified when:**

- Parts are quarantined
- Orders have quality holds
- Dispositions affect schedule
- First Piece Inspection (FPI) results are recorded

Check **Inbox** for notifications.

!!! tip "First Piece Inspection"
    FPI status is visible on the QA Work Orders page. When FPI fails, production should stop until the issue is resolved. Coordinate with QA to expedite FPI reviews for critical orders.

---

### 5.2 Responding to Holds

**When parts are held:**

1. Understand the issue
2. Assess impact on schedule
3. Coordinate with QA on timing
4. Update customer if needed
5. Adjust other priorities

**Exercise 5.1:** Handle a Quality Hold

1. Find order "TRAIN-HOLD"
2. Review which parts are quarantined
3. Check the quality report
4. Assess schedule impact

---

### 5.3 Expediting with QA

**For urgent orders:**

- Contact QA Manager
- Explain business impact
- Request prioritized disposition
- Don't pressure for bad decisions

---

### 5.4 After Disposition

**When parts are released:**

- Return to production
- May need rework step
- Update schedule
- Communicate to floor

---

### Knowledge Check: Module 5

1. Where do you see notifications about quality holds?
2. What should you do when parts are quarantined on a rush order?
3. What's the right way to request expedited QA review?

---

## Module 6: Customer Communication

### Learning Objectives

By the end of this module, you will:

- [ ] Provide accurate status updates
- [ ] Handle delay notifications professionally
- [ ] Document customer interactions

### 6.1 Status Inquiries

**When customers ask:**

1. Look up order on Tracker
2. Check current progress
3. Review any quality holds
4. Calculate realistic ETD
5. Provide honest update

---

### 6.2 Delay Notification

**When orders will be late:**

1. Identify as early as possible
2. Document the reason
3. Calculate new estimate
4. Notify customer proactively
5. Update order notes

**Don't wait until the due date!**

---

### 6.3 Documentation

**Record in order notes:**

- Customer communications
- Agreed changes
- Delay reasons
- New commitments

This creates an audit trail.

---

## Module 7: Daily Production Manager Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Follow an effective daily routine
- [ ] Prioritize your activities
- [ ] Communicate effectively

### 7.1 Morning Review

1. **Check Inbox** for overnight alerts
2. **Review Tracker** for at-risk orders
3. **Check quality holds** that need attention
4. **Identify priorities** for the day
5. **Brief team** on focus areas

---

### 7.2 During Day

- Monitor progress
- Address issues as they arise
- Coordinate with QA and shipping
- Adjust priorities as needed
- Update customers when required

---

### 7.3 End of Day

- Review day's progress
- Note issues for next day
- Update any at-risk orders
- Prepare handoff if needed

---

### 7.4 Weekly Tasks

- [ ] Review order book
- [ ] Check on-time delivery rate
- [ ] Capacity planning for next week
- [ ] Team scheduling
- [ ] Management report

---

## Practical Assessment

### Task 1: Order Creation

1. Create order "ASSESS-PM-001"
2. Add 5 parts
3. Set appropriate priority
4. Add notes

### Task 2: Work Order Setup

1. Create work order for ASSESS-PM-001
2. Select appropriate process
3. Assign equipment

### Task 3: Status Review

1. Review Tracker page
2. Identify the most at-risk order
3. Determine the cause
4. Propose action

### Task 4: Quality Coordination

1. Find order with quality hold
2. Review the quality report
3. Determine schedule impact
4. Draft customer communication

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Demonstrated with supervisor

### Competencies Verified

- [ ] Can create orders correctly
- [ ] Can add parts appropriately
- [ ] Can create and configure work orders
- [ ] Understands production monitoring
- [ ] Can coordinate with quality
- [ ] Communicates effectively about status

---

## Quick Reference

### Create Order
Orders → **+ New** → Fill details → Save → Add Parts

### Create Work Order
Work Orders → **+ New** → Select order, process → Save

### Check Status
Tracker → Find order → Review progress, holds

### Change Priority
Open work order → Change priority → Save → Notify floor

---

## Next Steps

After completing this training:

1. Shadow current Production Manager
2. Handle orders with oversight
3. Manage section independently
4. Full production responsibility

