# QA trainer packet — source material

Everything needed to build a QA training packet for UQMES, gathered in one
place. All of it is built around a single demo work order, **WO-QA-INSPECT-01**,
in the Demo Company tenant.

## Contents

| File | What it is |
|---|---|
| `UQMES_ONBOARDING_WALKTHROUGH.md` | The spine — a self-serve, first-person walkthrough that takes a QA inspector (Sarah) through a demo work order end to end (§1–§12), flags the QA **manager's** gates, and adds a manager section (§13), a process/DWI authoring section (§14), a Quality Reports section (§15), a glossary (§16), and a sidebar-reference appendix. Effective for a lone inspector or a lone manager. |
| `WO-QA-INSPECT-01_reference.md` | The work-order reference: WO-QA-INSPECT-01's identity, its 12-operation routing with QA gates, and the exact pre-staged state of all 8 parts mapped to the walkthrough sections they drive. Plus demo logins and reset instructions. |
| `QA_INSPECTOR_TRAINING_SCRIPT.md` | The existing trainer-facing script — role-play, checkpoints, and gotcha essays. The walkthrough deliberately stays lighter than this and points to it for the pedagogy. |
| `artifacts/WO-QA-INSPECT-01_traveler.pdf` | Scannable traveler PDF for the walk — the paper counterpart to the routing table, with the header barcode/QR and per-operation sign-off blocks. |

## How they fit together

- The **walkthrough** is the narrative. It references the **traveler PDF**
  (relative link `artifacts/…`) and the **training script** (relative link) —
  both are in this directory, so those links resolve within the packet.
- The **WO reference** is the fact sheet the walkthrough runs against: read it
  to know what each part is staged for before following a section.
- The **training script** is the instructor's companion if the packet is
  taught live rather than self-served.

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
