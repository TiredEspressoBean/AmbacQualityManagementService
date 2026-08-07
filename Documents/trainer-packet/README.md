# QA trainer packet — source material

Everything needed to build a QA training packet for UQMES, gathered in one
place. All of it is built around a single demo work order, **WO-QA-INSPECT-01**,
in the Demo Company tenant.

## Contents

| File | What it is |
|---|---|
| `UQMES_ONBOARDING_WALKTHROUGH.md` | The spine — a self-serve, first-person walkthrough that takes a QA inspector (Sarah) through a demo work order end to end (§1–§12), flags the QA **manager's** gates, and adds a manager section (§13), a process/DWI authoring section (§14), a Quality Reports section (§15), a glossary (§16), and a sidebar-reference appendix. Effective for a lone inspector or a lone manager. |
| `WO-QA-INSPECT-01_reference.md` | The work-order reference: WO-QA-INSPECT-01's identity, its 12-operation routing with QA gates, and the exact pre-staged state of all 8 parts mapped to the walkthrough sections they drive. Plus demo logins and reset instructions. |
| `QA_INSPECTOR_TRAINING_SCRIPT.md` | The trainer's script — the taught, classroom version of the walkthrough. Same WO-QA-INSPECT-01 scenario, turned into eleven inspector "journeys" with trainer prep, per-journey why / steps / checkpoint / watch-for, and an optional manager block. Cross-references the walkthrough by section. |
| `artifacts/WO-QA-INSPECT-01_traveler.pdf` | Scannable traveler PDF for the walk — the paper counterpart to the routing table, with the header barcode/QR and per-operation sign-off blocks. |

## How they fit together

- The **walkthrough** is the narrative. It references the **traveler PDF**
  (relative link `artifacts/…`), which is in this directory.
- The **WO reference** is the fact sheet the walkthrough runs against: read it
  to know what each part is staged for before following a section.
- The **training script** is the same content taught, not read: run it at a
  workstation with the trainee. It shares the walkthrough's scenario, so the
  two never disagree. Two things a trainer should know going in:
  - **Journey 6 needs Maria.** The disposition-decision co-sign (§6b) can't be
    completed on the inspector's login alone — keep the QA Manager's credentials
    handy. The script calls this out where it happens.
  - **Screenshots aren't captured yet.** The script was built onto this
    scenario and its inline screenshot references were removed rather than ship
    stale ones from the old scenario; teach from the live screen and recapture
    per the script's *Refreshing screenshots* section when convenient.

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
