"""
Demo DWI seeder — authors digital work instructions (Substep.body_blocks)
on the Injector Reman steps.

Gives the operator runtime + authoring UI a real story: inspection steps get
3D part callouts + defect annotation, measurement captures wired to the
demo MeasurementDefinitions, attestation/signature gates, and scan/photo
captures.

`body_blocks` is a TipTap document (`{type: 'doc', content: [...]}`) mirroring
the node vocabulary in `ambac-tracker-ui/src/types/dwi.ts`. node_ids are
deterministic UUIDv5s so re-seeding is stable and each capture node is unique
(satisfies the server-side node_id contract).
"""

import uuid

from Tracker.models import Substep, SubstepScope

from ..base import BaseSeeder


# Fixed namespace so node_ids are deterministic across re-seeds.
_NS = uuid.uuid5(uuid.NAMESPACE_URL, "uqmes-demo-dwi")


def _nid(*parts):
    """Deterministic UUID node_id from a stable key."""
    return str(uuid.uuid5(_NS, ":".join(str(p) for p in parts)))


# ---------------------------------------------------------------------------
# TipTap node builders (mirror the frontend SAMPLE_* shapes)
# ---------------------------------------------------------------------------

def _text(s):
    return {"type": "text", "text": s}


def _para(s=""):
    return {"type": "paragraph", "content": [_text(s)] if s else []}


def _heading(s, level=3):
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(s)]}


def _callout(variant, text):
    return {
        "type": "callout",
        "attrs": {"variant": variant},
        "content": [{"type": "paragraph", "content": [_text(text)]}],
    }


def _measurement(step, key, md, characteristic=""):
    """measurementInput wired to a real MeasurementDefinition."""
    return {
        "type": "measurementInput",
        "attrs": {
            "node_id": _nid(step, key),
            "label": md.label,
            "unit": md.unit or "",
            "nominal": float(md.nominal) if md.nominal is not None else None,
            "upper_tol": float(md.upper_tol) if md.upper_tol is not None else None,
            "lower_tol": float(md.lower_tol) if md.lower_tol is not None else None,
            "required": True,
            "characteristic_number": characteristic,
            "measurement_definition_id": str(md.id),
        },
    }


def _attest_confirm(step, key, label, prompt, required=True):
    return {
        "type": "attestationCheckpoint",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "kind": "confirm",
            "prompt": prompt,
            "required": required,
        },
    }


def _attest_signature(step, key, label, required=True):
    return {
        "type": "attestationCheckpoint",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "kind": "signature",
            "required": required,
        },
    }


def _photo(step, key, label, required=False):
    return {"type": "photoCapture", "attrs": {"node_id": _nid(step, key), "label": label, "required": required}}


def _scan(step, key, label, required=True):
    return {"type": "scanInput", "attrs": {"node_id": _nid(step, key), "label": label, "required": required}}


def _quality_status(step, key, label, required=True):
    return {
        "type": "qualityStatusField",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "required": required,
            "allowed": ["PASS", "FAIL", "PENDING"],
        },
    }


def _equipment_roles(step, key, label="Equipment used during this inspection", required=True):
    return {
        "type": "equipmentRolesField",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "required": required,
            "min_rows": 1,
            "default_role": "PRODUCTION",
        },
    }


def _inspection_signatures(step, key, label="Inspection sign-off",
                           require_detected=True, require_verified=False):
    return {
        "type": "inspectionSignatures",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "require_detected": require_detected,
            "require_verified": require_verified,
        },
    }


def _error_types(step, key, label="Defects observed", required=False, min_rows=0):
    return {
        "type": "errorTypesField",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "required": required,
            "min_rows": min_rows,
            "default_severity": "MAJOR",
        },
    }


def _callout_point(step, n, x, y, z, label):
    """A single numbered callout, with a saved camera framing aimed at it."""
    return {
        "id": _nid(step, "callout", n),
        "n": n,
        "x": x,
        "y": y,
        "z": z,
        "label": label,
        "view": {"position": [x * 1.8 + 2.0, y + 1.5, z * 1.8 + 2.0], "target": [x, y, z]},
    }


def _part_callout(label, model_id, points):
    return {"type": "partCallout", "attrs": {"label": label, "model_id": model_id, "callouts": points}}


def _part_annotation(step, key, label, model_id, required=True):
    return {
        "type": "partAnnotation",
        "attrs": {
            "node_id": _nid(step, key),
            "label": label,
            "model_id": model_id,
            "required": required,
            "default_view": {"position": [2.0, 2.0, 2.0], "target": [0.0, 0.0, 0.0]},
        },
    }


def _doc(*blocks):
    return {"type": "doc", "content": list(blocks)}


class DemoDwiSeeder(BaseSeeder):
    """Seeds Substep work-instruction content on the demo process steps."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, manufacturing, models_3d, receiving=None, outside_process=None):
        self.log("Creating demo DWI work instructions (substeps)...")

        steps = {s.name: s for s in (manufacturing.get("steps", []) if manufacturing else [])}
        # The RECEIVING and OSP steps are authored by their own seeders, not the
        # manufacturing one — merge them in so their work instructions get authored too.
        recv_step = receiving.get("step") if isinstance(receiving, dict) else None
        osp_step = outside_process.get("step") if isinstance(outside_process, dict) else None
        for extra in (recv_step, osp_step):
            if extra is not None:
                steps[extra.name] = extra

        md = {m.label: m for m in (manufacturing.get("measurement_definitions", []) if manufacturing else [])}
        models = models_3d.get("3d_models", []) if models_3d else []
        model_id = str(models[0].id) if models else ""

        content = self._content(md, model_id, recv_step=recv_step, osp_step=osp_step)

        created = 0
        for step_name, substeps in content.items():
            step = steps.get(step_name)
            if not step:
                self.log(f"  Skipping '{step_name}' (step not found)", warning=True)
                continue
            for ss in substeps:
                Substep.objects.update_or_create(
                    tenant=self.tenant,
                    step=step,
                    title=ss["title"],
                    defaults={
                        "order": ss["order"],
                        "body_blocks": ss["body"],
                        "is_optional": ss.get("is_optional", False),
                        "is_critical": ss.get("is_critical", False),
                        "allow_not_applicable": ss.get("allow_not_applicable", False),
                        "requires_signature": ss.get("requires_signature", False),
                        "is_inspection_point": ss.get("is_inspection_point", False),
                        # BATCH-scope substeps run once per load (BatchExecution);
                        # default SAMPLED runs per part.
                        "scope": ss.get("scope", SubstepScope.SAMPLED),
                    },
                )
                created += 1

        self.log(f"  Created {created} substeps across {len(content)} steps")
        return {"substeps_created": created}

    def _content(self, md, model_id, recv_step=None, osp_step=None):
        """Map step name -> list of substeps. Built at seed time so measurement
        and 3D-model ids are the real seeded rows."""

        def maybe_measure(step, key, label, characteristic=""):
            """Measurement node only if the demo definition exists."""
            m = md.get(label)
            return [_measurement(step, key, m, characteristic)] if m else []

        def step_measures(step, step_name, characteristic=""):
            """Measurement nodes for every MeasurementDefinition on a step (used for
            the RECEIVING / OSP steps, whose defs live on the step itself, not in the
            manufacturing measurement_definitions map)."""
            if step is None:
                return []
            from Tracker.models import MeasurementDefinition
            nodes = []
            for m in MeasurementDefinition.objects.filter(step=step, type="NUMERIC"):
                nodes.append(_measurement(step_name, f"measure-{m.id}", m, characteristic))
            return nodes

        callout_block = (
            [
                _part_callout(
                    "Nozzle inspection points",
                    model_id,
                    [
                        _callout_point("Nozzle Inspection", 1, -0.286, -0.134, 1.042, "Nozzle tip — check for scoring/erosion"),
                        _callout_point("Nozzle Inspection", 2, 0.471, -0.308, 0.595, "Spray-hole bank — verify all holes clear"),
                        _callout_point("Nozzle Inspection", 3, 0.300, -0.184, 0.616, "Seat face — inspect for pitting"),
                    ],
                )
            ]
            if model_id
            else []
        )

        content = {
            "Core Receiving": [
                {
                    "title": "Receive and log incoming core",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Receive the incoming core, scan its identity band, and log its arrival condition."),
                        _callout("note", "Cores arrive as-is from the field — record what you see, don't clean yet."),
                        _scan("Core Receiving", "core-serial", "Scan core serial / identity band"),
                        _photo("Core Receiving", "arrival-photo", "Photograph the core as received", required=False),
                        _quality_status("Core Receiving", "arrival-condition", "Arrival condition"),
                        _inspection_signatures("Core Receiving", "receiving-signoff", require_detected=True),
                    ),
                },
            ],
            "Component Grading": [
                {
                    "title": "Grade and sort components",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Grade each harvested component"),
                        _para("Assess each component against the grading criteria and sort into reuse / rework / scrap."),
                        _callout("caution", "When in doubt, grade down — a reused-but-marginal component fails downstream."),
                        _quality_status("Component Grading", "grade-result", "Grade decision"),
                        _error_types("Component Grading", "grade-defects", "Defects driving the grade", min_rows=0),
                        _inspection_signatures("Component Grading", "grade-signoff", require_detected=True),
                    ),
                },
            ],
            "Disassembly": [
                {
                    "title": "Tear down injector",
                    "order": 0,
                    "body": _doc(
                        _para("Disassemble the injector into its component groups. Bag and tag each subassembly."),
                        _callout("note", "Keep the core's identity band with the body group until grading."),
                        _scan("Disassembly", "core-serial", "Scan core serial / identity band"),
                        _photo("Disassembly", "teardown-photo", "Photograph the teardown layout", required=False),
                    ),
                },
            ],
            "Cleaning": [
                {
                    "title": "Load parts into the cleaner",
                    "order": 0,
                    "body": _doc(
                        _para("Scan each part as you load it into the ultrasonic basket. Every part in this load is cleaned together."),
                        _scan("Cleaning", "load-scan", "Scan each part into the load"),
                    ),
                },
                {
                    "title": "Run ultrasonic wash cycle",
                    "order": 1,
                    # BATCH scope: one cycle cleans the whole basket, so the
                    # capture binds to the load's BatchExecution, not per part.
                    "scope": SubstepScope.BATCH,
                    # Inspection point: the bath-temperature reading below is a
                    # cycle-level QA measurement, so this substep promotes to a
                    # batch-scoped QualityReport (PASS/FAIL on the whole load).
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Ultrasonic clean — whole load"),
                        _callout("note", "One cycle cleans the entire basket; the result applies to every part in the load."),
                        # Cycle-level reading: bath temp is measured once for the
                        # load. Binds to the BatchExecution (StepExecutionMeasurement
                        # + a batch QualityReport), not to any one part.
                        *maybe_measure("Cleaning", "bath-temp", "Bath Temperature"),
                        _attest_confirm("Cleaning", "cycle-done", "Cycle complete", "Confirm the wash and rinse cycle finished and the basket was inspected."),
                    ),
                },
            ],
            "Nozzle Inspection": [
                {
                    "title": "Visual nozzle inspection",
                    "order": 0,
                    # Inspection point: the defect annotator + Pass/Fail + the QR
                    # capture bundle only record to a QualityReport when this is
                    # True (operator_capture.py). Mirrors what the substep editor
                    # now enforces when an annotator is present.
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Inspect the nozzle"),
                        _callout("caution", "Handle the nozzle tip with lint-free gloves — fingerprints etch the seat."),
                        *callout_block,
                        _part_annotation("Nozzle Inspection", "defects", "Mark any defects you find on the model", model_id),
                        # QualityReport capture bundle (status already present above):
                        _quality_status("Nozzle Inspection", "visual-result", "Visual inspection result"),
                        _equipment_roles("Nozzle Inspection", "equipment"),
                        _inspection_signatures("Nozzle Inspection", "signoff-sig"),
                        _error_types("Nozzle Inspection", "defect-types"),
                    ),
                },
                {
                    "title": "Measure spray angle",
                    "order": 1,
                    "is_inspection_point": True,
                    "requires_signature": True,
                    "body": _doc(
                        _para("Mount the nozzle on the spray rig and record the measured spray angle."),
                        *maybe_measure("Nozzle Inspection", "spray-angle", "Spray Angle", characteristic="N-12"),
                        _attest_signature("Nozzle Inspection", "signoff", "Inspector sign-off"),
                    ),
                },
            ],
            "Flow Testing": [
                {
                    "title": "Flow test",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Run the flow test cycle and record the measured flow rate at rated pressure."),
                        _scan("Flow Testing", "part-scan", "Scan the part barcode"),
                        *maybe_measure("Flow Testing", "flow-rate", "Flow Rate", characteristic="F-04"),
                        _attest_confirm(
                            "Flow Testing",
                            "bench-confirm",
                            "Flow bench in-calibration",
                            "I confirm the flow bench calibration is current.",
                        ),
                    ),
                },
            ],
            "Assembly": [
                {
                    "title": "Reassemble and torque",
                    "order": 0,
                    "is_critical": True,
                    "body": _doc(
                        _para("Reassemble the injector with new seals, then torque the retaining nut to spec."),
                        _callout("caution", "Torque is safety-critical — use the calibrated wrench and the recorded value."),
                        *maybe_measure("Assembly", "torque", "Assembly Torque", characteristic="A-01"),
                        _attest_confirm(
                            "Assembly",
                            "new-seals",
                            "New seals installed",
                            "I confirm new seals were used (no reused seals).",
                        ),
                    ),
                },
            ],
            "Final Test": [
                {
                    "title": "Final leak / pressure test",
                    "order": 0,
                    "is_inspection_point": True,
                    "requires_signature": True,
                    "body": _doc(
                        _para("Pressurize and hold; record the leak-test pressure and the pass/fail result."),
                        *maybe_measure("Final Test", "leak-pressure", "Leak Test Pressure", characteristic="FT-07"),
                        _quality_status("Final Test", "final-result", "Final test result"),
                        _attest_signature("Final Test", "release-signoff", "Release sign-off"),
                    ),
                },
            ],
        }

        # Receiving inspection (Flow A) — DWI-based incoming inspection. Runs the
        # RECEIVING_COMPLETION adapter: unit-by-unit capture → verdict → accept/reject.
        if recv_step is not None:
            content[recv_step.name] = [
                {
                    "title": "Inspect incoming material",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Incoming inspection"),
                        _para("Inspect the sampled units against the receiving characteristics, then set the verdict."),
                        _callout("note", "Sample size and accept/reject come from the receiving sampling plan (C=0 / AQL)."),
                        _scan(recv_step.name, "lot-scan", "Scan the lot / packing slip", required=False),
                        *step_measures(recv_step, recv_step.name, characteristic="RCV-01"),
                        _quality_status(recv_step.name, "recv-result", "Incoming inspection result"),
                        _inspection_signatures(recv_step.name, "recv-signoff", require_detected=True),
                        _error_types(recv_step.name, "recv-defects", "Defects found", min_rows=0),
                    ),
                },
            ]

        # Outside processing (Flow B) — return inspection. Runs the OSP_COMPLETION
        # adapter: accept advances the parts, reject quarantines for disposition.
        if osp_step is not None:
            content[osp_step.name] = [
                {
                    "title": "Return inspection (post-coating)",
                    "order": 0,
                    "is_inspection_point": True,
                    "requires_signature": True,
                    "body": _doc(
                        _heading("Inspect returned subcontract work"),
                        _para("Verify the coating on the returned parts and record the measured thickness."),
                        _callout("caution", "Reject the shipment if thickness is out of tolerance — it routes to disposition."),
                        *step_measures(osp_step, osp_step.name, characteristic="OSP-01"),
                        _photo(osp_step.name, "coating-photo", "Photograph the coated surface", required=False),
                        _quality_status(osp_step.name, "osp-result", "Return inspection result"),
                        _attest_signature(osp_step.name, "osp-signoff", "Return inspection sign-off"),
                    ),
                },
            ]

        return content
