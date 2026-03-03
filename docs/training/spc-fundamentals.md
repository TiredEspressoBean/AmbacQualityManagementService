# SPC Fundamentals Training

**Duration:** 1-2 hours
**Prerequisites:** Basic understanding of your role (Operator, QA Inspector, or QA Manager)
**Goal:** Understand how to read and respond to SPC charts in your daily work

---

## Who Should Take This Training

This module covers Statistical Process Control basics for:

- **Operators**: Recognize when your process is drifting
- **QA Inspectors**: Understand measurement trends and flag issues
- **QA Managers**: Review SPC data and make process decisions

---

## Module 1: What is SPC?

### Learning Objectives

By the end of this module, you will:

- [ ] Understand why SPC matters
- [ ] Know the difference between common and special cause variation
- [ ] Recognize control charts

### 1.1 Why SPC Matters

Every manufacturing process has **variation**. SPC helps you:

- **Detect problems early** - Before defects occur
- **Reduce scrap and rework** - Catch drift before parts fail
- **Improve consistency** - Understand your process capability

!!! example "Demo: Flow Rate Variation"
    In demo mode, view the Flow Testing SPC chart. Notice how Flow Rate measurements vary between 115-125 mL/min even when the process is stable. This is normal variation. SPC helps distinguish normal variation from problems.

### 1.2 Two Types of Variation

| Type | Cause | Action |
|------|-------|--------|
| **Common Cause** | Normal process variation (materials, environment) | None - this is expected |
| **Special Cause** | Something changed (tool wear, bad material, operator error) | Investigate and fix |

**Key insight:** SPC charts help you tell these apart.

### 1.3 The Control Chart

```
UCL ─────────────────────────────────────  ← Upper Control Limit
         *    *
    *        *   *  *    *
CL  ─────*────────────────*────*──────────  ← Center Line (average)
           *     *    *      *
LCL ─────────────────────────────────────  ← Lower Control Limit
```

- **UCL/LCL**: Calculated from YOUR process data (not specs)
- **CL**: The average of your measurements
- **Points**: Each measurement (or group average)

**The rule:** Points should scatter randomly between the limits. Patterns = problems.

---

### Knowledge Check: Module 1

1. What's the difference between common cause and special cause variation?
2. Where do control limits come from?
3. If a point is between the control limits, is the process definitely OK?

---

## Module 2: Reading Control Charts

### Learning Objectives

By the end of this module, you will:

- [ ] Identify out-of-control signals
- [ ] Recognize trends and patterns
- [ ] Know when to escalate

### 2.1 Out-of-Control Signals

The system flags these patterns automatically:

| Signal | What It Looks Like | What It Means |
|--------|-------------------|---------------|
| **Point beyond limits** | Single point above UCL or below LCL | Immediate problem |
| **Run** | 8+ points on same side of center | Process shifted |
| **Trend** | 6+ points going up or down | Process drifting |
| **Alternating** | Points zigzag up-down-up-down | Measurement or equipment issue |

!!! warning "Red Points = Action Needed"
    When you see a red-highlighted point on an SPC chart, this is a signal. Don't ignore it.

### 2.2 Demo: SPC Violation

In demo mode, the Flow Rate chart shows a **Rule 2 violation** (2 of 3 points beyond 2σ):

1. Navigate to **Analytics > SPC**
2. Select Process: Common Rail Injector Remanufacturing
3. Select Step: Flow Testing
4. Select Measurement: Flow Rate @ 1000 bar
5. Look for the red-highlighted points

This triggered an alert for QA Inspector Sarah Chen.

### 2.3 Control Limits vs Specification Limits

**This is critical to understand:**

| Type | Source | Meaning |
|------|--------|---------|
| **Control Limits (UCL/LCL)** | Calculated from process data | What the process IS doing |
| **Specification Limits (USL/LSL)** | Engineering drawing | What the process SHOULD do |

A process can be:
- **In control but not capable**: Stable but making bad parts
- **Out of control but within spec**: Unstable but still passing

**Both matter.** SPC monitors stability. Specs define acceptance.

---

### Exercise 2.1: Identify Signals

Look at these patterns and identify the signal type:

**Pattern A:**
```
     *
         *
             *
                 *
                     *
```
Answer: _______________

**Pattern B:**
```
    *   *   *   *   *   *   *   *   *
─────────────────────────────────────────
```
Answer: _______________

**Pattern C:**
```
                                    *   ← beyond UCL
─────────────────────────────────────────
    *   *   *   *   *   *   *
```
Answer: _______________

---

### Knowledge Check: Module 2

1. What does it mean when 8 consecutive points are above the center line?
2. A point is beyond the control limit but within the specification limit. Is this a problem?
3. Who should you notify when you see a red-flagged point?

---

## Module 3: Role-Specific Responses

### 3.1 For Operators

**What you see:** SPC chart on your workstation or dashboard

**Your responsibilities:**

| Signal | Action |
|--------|--------|
| Green (normal) | Continue working |
| Yellow (warning) | Pay attention, check next few parts carefully |
| Red (out-of-control) | **Stop and notify supervisor or QA** |

**You are NOT expected to:**
- Diagnose the root cause
- Adjust the process without approval
- Ignore red signals "because parts are still passing"

!!! tip "Demo: Operator View"
    Log in as Mike Rodriguez (mike.ops@demo.ambac.com). If SPC alerts are configured for your workstation, you'd see a banner when Flow Testing shows a violation.

### 3.2 For QA Inspectors

**What you see:** SPC charts during measurement review

**Your responsibilities:**

| Signal | Action |
|--------|--------|
| Point beyond limits | Document on quality report, flag for investigation |
| Trend developing | Note in inspection comments, alert QA Manager |
| Capability declining | Include in shift report |

**Key questions to ask:**
- When did this start?
- What changed (material lot, operator, equipment)?
- Are other measurements affected?

!!! tip "Demo: Inspector View"
    Log in as Sarah Chen (sarah.qa@demo.ambac.com). Check your Inbox for the SPC violation alert on Flow Rate. This is how the system notifies inspectors of statistical issues.

### 3.3 For QA Managers

**What you see:** SPC dashboard and capability reports

**Your responsibilities:**

| Metric | Action |
|--------|--------|
| Out-of-control points | Ensure investigation occurs, connect to CAPA if recurring |
| Cpk < 1.33 | Initiate process improvement |
| Cpk declining | Investigate before it becomes critical |
| Baseline needs update | Review and approve new baseline |

**Manager decisions:**
- When to freeze/update baselines
- When to trigger CAPA from SPC data
- How to prioritize capability improvements

!!! tip "Demo: Manager View"
    Log in as Jennifer Walsh (jennifer.mgr@demo.ambac.com). Review the Analytics dashboard to see overall capability status. CAPA-2024-003 was partially triggered by SPC data showing nozzle measurement drift.

---

## Module 4: Capability Basics

### Learning Objectives

By the end of this module, you will:

- [ ] Understand Cp and Cpk
- [ ] Interpret capability status
- [ ] Know target values

### 4.1 What is Capability?

**Capability** answers: Can this process meet specifications?

| Index | Question | Formula |
|-------|----------|---------|
| **Cp** | How capable could we be? | (USL - LSL) / 6σ |
| **Cpk** | How capable are we actually? | Accounts for centering |

### 4.2 Interpreting Cpk

| Cpk | Status | Meaning |
|-----|--------|---------|
| < 1.0 | Not capable | Process makes defects |
| 1.0 - 1.33 | Marginal | Barely acceptable |
| 1.33 - 1.67 | Capable | Good |
| > 1.67 | Highly capable | Excellent |

**Target:** Most industries require Cpk ≥ 1.33

### 4.3 Common Scenarios

| Cp | Cpk | Problem |
|----|-----|---------|
| High | Low | Process not centered (adjust aim) |
| Low | Low | Too much variation (reduce spread) |
| High | High | Good process! |

!!! example "Demo: Flow Rate Capability"
    The demo Flow Rate measurement shows Cpk = 1.45 (Capable). This means the flow testing process can reliably produce parts within the 105-135 mL/min specification.

---

### Knowledge Check: Module 4

1. What does Cpk = 0.9 tell you?
2. If Cp is high but Cpk is low, what's the likely issue?
3. What is the typical minimum acceptable Cpk?

---

## Module 5: Practical Application

### Exercise 5.1: Navigate to SPC

1. Log into the demo environment
2. Navigate to **Analytics > SPC**
3. Select:
   - Process: Common Rail Injector Remanufacturing
   - Step: Flow Testing
   - Measurement: Flow Rate @ 1000 bar
4. Answer:
   - What is the current Cpk? ___
   - Are there any red-flagged points? ___
   - What is the date range shown? ___

### Exercise 5.2: Interpret a Chart

Using the same SPC view:

1. Identify the UCL and LCL values
2. Find the center line value
3. Count how many points are above vs below center
4. Look for any patterns (trends, runs, clusters)
5. Write a one-sentence summary of what you see

### Exercise 5.3: Role-Based Response

**Scenario:** You see 3 consecutive points trending upward toward the UCL.

**If you're an Operator:** What do you do? _______________

**If you're a QA Inspector:** What do you do? _______________

**If you're a QA Manager:** What do you do? _______________

---

## Quick Reference Card

### Control Chart Signals

| Pattern | Name | Action |
|---------|------|--------|
| Point outside limits | Out-of-control | Stop, investigate |
| 8 points same side | Run | Process shifted |
| 6 points trending | Trend | Process drifting |
| Alternating pattern | Oscillation | Check measurement |

### Capability Quick Guide

| Cpk | Status | Color |
|-----|--------|-------|
| ≥ 1.67 | Excellent | Green |
| 1.33 - 1.67 | Good | Green |
| 1.0 - 1.33 | Marginal | Yellow |
| < 1.0 | Not capable | Red |

### Escalation Path

```
Operator sees red signal
       ↓
Notify QA Inspector / Supervisor
       ↓
Inspector investigates
       ↓
QA Manager reviews if needed
       ↓
CAPA if recurring issue
```

---

## Practical Assessment

### Scenario

You are reviewing the SPC chart for Spray Pattern Angle. You notice:
- Last 7 points are all below the center line
- Cpk has dropped from 1.5 to 1.2 over the past week
- No points are outside control limits yet

**Questions:**

1. Is this process in control? Why or why not?
2. What type of variation signal do you see?
3. What would you recommend as next steps?
4. Should this trigger a CAPA? Why or why not?

---

## Summary

### Key Takeaways

1. **SPC detects problems before defects occur** - It's proactive quality
2. **Control limits come from the process** - Not from specifications
3. **Patterns matter** - Not just individual points
4. **Know your role** - Operators flag, Inspectors investigate, Managers decide
5. **Cpk ≥ 1.33 is the target** - Below that needs attention

### Next Steps

- Practice reading SPC charts in demo mode
- Know where to find SPC in your daily workflow
- Understand your escalation path
- **For QA Managers/Engineers**: Review the [SPC Practitioner Guide](../analysis/spc-practitioner-guide.md) for investigation workflows and CAPA criteria

---

## Sign-Off

**Trainee Acknowledgment:**

I have completed the SPC Fundamentals training and understand:

- [ ] How to read control charts
- [ ] What out-of-control signals look like
- [ ] My role-specific responsibilities
- [ ] When to escalate

**Trainee:** _________________ **Date:** _________

**Trainer:** _________________ **Date:** _________
