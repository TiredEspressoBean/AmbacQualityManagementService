# QA trainer packet — source material

Everything needed to build a QA training packet for UQMES, gathered in one
place. All of it is built around a single demo work order, **WO-QA-INSPECT-01**,
in the Demo Company tenant.

## Contents

| File | What it is |
|---|---|
| `UQMES_ONBOARDING_WALKTHROUGH.md` | The spine — a self-serve, first-person walkthrough that takes a QA inspector (Sarah) through a demo work order end to end (§1–§12), flags the QA **manager's** gates, and adds a manager section (§13), a process/DWI authoring section (§14), a Quality Reports section (§15), a glossary (§16), and a sidebar-reference appendix. Effective for a lone inspector or a lone manager. |
| `WO-QA-INSPECT-01_reference.md` | The work-order reference: WO-QA-INSPECT-01's identity, its 12-operation routing with QA gates, and the exact pre-staged state of all 8 parts mapped to the walkthrough sections they drive. Plus demo logins and reset instructions. |
| `artifacts/WO-QA-INSPECT-01_traveler.pdf` | Scannable traveler PDF for the walk — the paper counterpart to the routing table, with the header barcode/QR and per-operation sign-off blocks. |

## How they fit together

- The **walkthrough** is the narrative. It references the **traveler PDF**
  (relative link `artifacts/…`), which is in this directory.
- The **WO reference** is the fact sheet the walkthrough runs against: read it
  to know what each part is staged for before following a section.

> **Deliberately not included — the existing trainer script.** The walkthrough's
> "What this is not" points to `QA_INSPECTOR_TRAINING_SCRIPT.md`, a separate
> instructor runbook. It's left out on purpose: it's a valid, browser-verified
> curriculum, but built on a **different demo work order** — WO-2024-0042-A
> (serials `INJ-0042-###`) — not the WO-QA-INSPECT-01 scenario everything in
> this packet uses. It still lives in `Documents/` if you want it as a
> structural reference; just don't teach the two side by side. (It also predates
> the disposition co-sign gate this packet's walkthrough covers in §6b.)

## Demo setup

- Tenant: **Demo Company**. Logins all use password **`demo123`** —
  `sarah.qa@demo.ambac.com` (QA Inspector), `maria.qa@demo.ambac.com` (QA
  Manager), `mike.ops@demo.ambac.com` (Operator).
- Reset to the staged state with `cd PartsTracker && python manage.py
  seed_demo` before a session, and again after any destructive walk-through.
- Auto-generated record numbers (dispositions, quality reports, OSP shipments)
  rotate on each reseed — key training material to the **part and section**,
  not to a specific `DISP-2026-####` / `QR-2026-####` number.

## Note on source of truth

These are **copies**, assembled for convenience. The maintained originals live
in `Documents/` (and `Documents/artifacts/`); edit there, then refresh this
directory if the packet needs updating.
