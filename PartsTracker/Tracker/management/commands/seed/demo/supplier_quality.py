"""
Demo seeder for Supplier Quality Management (SQM).

Populates the surfaces the receiving/SQM work added, which the older receiving
seeder never touched:
  - **Approved Supplier List (ASL)** — SupplierQualification records across the
    lifecycle: APPROVED, CONDITIONAL, EXPIRED, and one *expiring soon* (exercises
    the `notify_expiring_qualifications` reminder).
  - **Part approvals (PPAP / FAI)** — a couple of PartApproval records.
  - **Certificate of Conformance** — attaches a CoC file to accepted lots so the
    scorecard's CoC-compliance metric is non-zero and the capture UI shows "on file".
  - **Qualification hold** — flags the part type as requiring qualification and
    receives a lot from an *unqualified* supplier, so it soft-holds in the queue.

The **standing-review badge** falls out for Great Lakes: it already has a rejected
lot + open SCAR (from the receiving seeder), and once it carries an APPROVED
qualification the scorecard breach surfaces a "Review: suspend" recommendation.

Runs after the receiving seeder (needs its RECEIVING step + sampling ruleset).
"""
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.utils import timezone

from Tracker.models import Companies, MaterialLot, PartApproval, SupplierQualification
from Tracker.services.qms import (
    supplier_qualification as sq,
    part_approval as pa,
    receiving_inspection,
)

from ..base import BaseSeeder


class DemoSupplierQualitySeeder(BaseSeeder):
    """Seeds ASL qualifications, part approvals, CoC files, and a qualification hold."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, companies, users, manufacturing, receiving):
        self.log("Creating demo supplier-quality data (ASL, part approvals, CoC)...")
        result = {"qualifications": [], "part_approvals": [], "coc_lots": 0, "held_lot": None}

        part_types = manufacturing.get("part_types", []) if isinstance(manufacturing, dict) else []
        if not part_types:
            self.log("  Warning: no part types, skipping SQM seed", warning=True)
            return result
        part_type = part_types[0]

        employees = users.get("employees", []) if isinstance(users, dict) else []
        user = employees[0] if employees else None

        company_map = companies.get("by_name", {}) if isinstance(companies, dict) else {}
        great_lakes = company_map.get("Great Lakes Diesel")
        today = timezone.now().date()

        # Extra supplier companies so the ASL shows distinct lifecycle states.
        def supplier(name, desc):
            c, _ = Companies.objects.update_or_create(
                tenant=self.tenant, name=name,
                defaults={"description": desc},
            )
            return c

        precision = supplier("Precision Castings Inc", "Castings supplier - qualification expiring soon.")
        forge = supplier("Midwest Forge Works", "Forgings supplier - conditionally approved.")
        apex = supplier("Apex Plating Co", "Plating subcontractor - qualification lapsed.")
        bargain = supplier("Bargain Bolts LLC", "Fasteners supplier - not yet qualified (held on receipt).")

        # --- ASL: SupplierQualification across the lifecycle ---
        def ensure_qual(supp, *, status, expiry_days, basis="AUDIT"):
            if supp is None:
                return None
            existing = (SupplierQualification.objects
                        .filter(supplier=supp, scope_type=SupplierQualification.SCOPE_PART_TYPE,
                                part_type=part_type).first())
            if existing:
                return existing
            q = sq.open_qualification(supplier=supp, part_type=part_type, basis=basis, user=user)
            if status in ("APPROVED", "CONDITIONAL"):
                sq.grant(q, user=user, conditional=(status == "CONDITIONAL"),
                         expiry_date=today + timedelta(days=expiry_days))
            elif status == "EXPIRED":
                # Seed a lapsed record directly (skip the emit the expire task would fire).
                q.status = "EXPIRED"
                q.effective_date = today - timedelta(days=400)
                q.expiry_date = today - timedelta(days=30)
                q.save(update_fields=["status", "effective_date", "expiry_date", "updated_at"])
            return q

        for supp, status, days in (
            (great_lakes, "APPROVED", 730),    # qualified primary → standing badge surfaces
            (precision, "APPROVED", 18),        # expiring soon → reminder fires
            (forge, "CONDITIONAL", 365),
            (apex, "EXPIRED", 0),
        ):
            q = ensure_qual(supp, status=status, expiry_days=days)
            if q:
                result["qualifications"].append(q)

        # --- Part approvals (PPAP / FAI) ---
        def ensure_approval(supp, *, approval_type, status, expiry_days, reference):
            if supp is None:
                return None
            existing = PartApproval.objects.filter(supplier=supp, part_type=part_type,
                                                   approval_type=approval_type).first()
            if existing:
                return existing
            a = pa.open_approval(part_type=part_type, supplier=supp, approval_type=approval_type,
                                 reference=reference, user=user)
            if status in ("APPROVED", "CONDITIONAL"):
                pa.grant(a, user=user, conditional=(status == "CONDITIONAL"),
                         expiry_date=today + timedelta(days=expiry_days))
            # status PENDING → leave as opened
            return a

        for supp, atype, status, days, ref in (
            (great_lakes, PartApproval.APPROVAL_PPAP, "APPROVED", 365, "PPAP-2026-GLD-001"),
            (precision, PartApproval.APPROVAL_FAI, "CONDITIONAL", 200, "FAI-2026-PCI-014"),
            (forge, PartApproval.APPROVAL_PPAP, "PENDING", 0, "PPAP-2026-MFW-007"),
        ):
            a = ensure_approval(supp, approval_type=atype, status=status, expiry_days=days, reference=ref)
            if a:
                result["part_approvals"].append(a)

        # --- Certificate of Conformance on accepted lots ---
        accepted = MaterialLot.objects.filter(material_type=part_type, status="ACCEPTED",
                                              certificate_of_conformance="")
        for lot in accepted:
            lot.certificate_of_conformance.save(
                f"coc_{lot.lot_number}.pdf",
                ContentFile(b"%PDF-1.4\n% Demo Certificate of Conformance\n"),
                save=True,
            )
            result["coc_lots"] += 1

        # --- Qualification hold: unqualified supplier soft-holds on receipt ---
        recv_step = receiving.get("step") if isinstance(receiving, dict) else None
        if recv_step is not None and user is not None:
            if not part_type.requires_supplier_qualification:
                part_type.requires_supplier_qualification = True
                part_type.save(update_fields=["requires_supplier_qualification"])
            held, created = MaterialLot.objects.update_or_create(
                tenant=self.tenant, lot_number=f"RCV-{part_type.ID_prefix or 'LOT'}-HOLD",
                defaults={
                    "material_type": part_type, "supplier": bargain,
                    "supplier_lot_number": "SUP-HOLD-001",
                    "erp_po_number": "PO-2026-HOLD",
                    "received_date": today, "received_by": user,
                    "quantity": Decimal("30"), "quantity_remaining": Decimal("30"),
                    "unit_of_measure": "EA", "status": "RECEIVED",
                    "storage_location": "Receiving Dock",
                },
            )
            if created or held.status == "RECEIVED":
                receiving_inspection.route_received_lot(held, user)
            result["held_lot"] = held

        self.log(f"  Created {len(result['qualifications'])} qualifications, "
                 f"{len(result['part_approvals'])} part approvals, "
                 f"CoC on {result['coc_lots']} lot(s), 1 held lot (unqualified supplier)")
        return result
