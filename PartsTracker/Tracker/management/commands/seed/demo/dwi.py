"""
Demo DWI seeder — authors digital work instructions (Substep.body_blocks)
on the Injector Reman and Injector Build steps.

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
    """measurementInput wired to a real MeasurementDefinition — the attrs the editor's
    linked-spec pick writes, gauges included: the runtime offers only the node's
    default/backup gauge, so a node without them has no gauge picker at all."""
    from Tracker.models import MeasurementDefinition
    # Re-read: the caller's instance comes from the manufacturing phase, before the
    # scheduling phase wired each spec's gauge.
    md = (MeasurementDefinition.objects.select_related('default_equipment', 'backup_equipment')
          .get(pk=md.pk))
    dflt, backup = md.default_equipment, md.backup_equipment
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
            "default_equipment_id": str(dflt.id) if dflt else None,
            "default_equipment_name": dflt.name if dflt else "",
            "default_equipment_status": dflt.status if dflt else None,
            "backup_equipment_id": str(backup.id) if backup else None,
            "backup_equipment_name": backup.name if backup else "",
            "backup_equipment_status": backup.status if backup else None,
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


def _reman_capture(node_type, step, key, label, required=True, **extra):
    """Reman teardown / rebuild capture (harvestedComponentCapture,
    componentInstallCapture, rebuildFindingCapture). They read the unit's core, so
    they belong on reman work; on a step new builds share, put them in their own
    substep that a new build can mark not-applicable."""
    return {"type": node_type, "attrs": {"node_id": _nid(step, key), "label": label,
                                         "required": required, **extra}}


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


def _step_measures(step, node_step, characteristic=""):
    """Measurement nodes for every numeric MeasurementDefinition on a step (the
    RECEIVING and OSP steps, whose definitions live on the step itself)."""
    if step is None:
        return []
    from Tracker.models import MeasurementDefinition
    return [_measurement(node_step, f"measure-{m.id}", m, characteristic)
            for m in MeasurementDefinition.objects.filter(step=step, type="NUMERIC")]


def _return_inspection(osp_step, node_step):
    """Outside processing (Flow B) return inspection. The OSP_COMPLETION adapter runs
    it: accept advances the parts, reject quarantines them for disposition."""
    return [
        {
            "title": "Return inspection (post-coating)",
            "order": 0,
            "is_inspection_point": True,
            "body": _doc(
                _heading("Inspect returned subcontract work"),
                _para("Verify the coating on the returned parts and record the measured thickness."),
                _callout("caution", "Reject the shipment if thickness is out of tolerance - it routes to disposition."),
                *_step_measures(osp_step, node_step, characteristic="OSP-01"),
                _photo(node_step, "coating-photo", "Photograph the coated surface", required=False),
                _quality_status(node_step, "osp-result", "Return inspection result"),
                _attest_signature(node_step, "osp-signoff", "Return inspection sign-off"),
            ),
        },
    ]


class DemoDwiSeeder(BaseSeeder):
    """Seeds Substep work-instruction content on the demo process steps."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, manufacturing, models_3d, receiving=None, outside_process=None):
        self.log("Creating demo DWI work instructions (substeps)...")

        manufacturing = manufacturing or {}
        route_steps = {
            "reman": dict(manufacturing.get("reman_steps", {})),
            "build": dict(manufacturing.get("build_steps", {})),
        }
        # The RECEIVING and OSP steps are authored by their own seeders, not the
        # manufacturing one: merge them in so their work instructions get authored too.
        recv_step = receiving.get("step") if isinstance(receiving, dict) else None
        osp = outside_process if isinstance(outside_process, dict) else {}
        if osp.get("step") is not None:
            route_steps["build"][osp["step"].name] = osp["step"]
        if osp.get("reman_step") is not None:
            route_steps["reman"][osp["reman_step"].name] = osp["reman_step"]

        # A measurement belongs to its route: labels repeat across the two.
        build_ids = {st.id for st in route_steps["build"].values()}
        md = {}
        for m in manufacturing.get("measurement_definitions", []):
            md[("build" if m.step_id in build_ids else "reman", m.label)] = m
        models = models_3d.get("3d_models", []) if models_3d else []
        model_id = str(models[0].id) if models else ""

        content = {
            "reman": self._reman_content(md, model_id, osp.get("reman_step")),
            "build": self._build_content(md, model_id, osp.get("step")),
        }
        if recv_step is not None:
            route_steps["receiving"] = {recv_step.name: recv_step}
            content["receiving"] = self._receiving_content(recv_step)

        created = 0
        authored = 0
        for route, route_content in content.items():
            for step_name, substeps in route_content.items():
                step = route_steps[route].get(step_name)
                if not step:
                    self.log(f"  Skipping {route} '{step_name}' (step not found)", warning=True)
                    continue
                authored += 1
                created += self._author(step, substeps)

        self.log(f"  Created {created} substeps across {authored} steps")
        return {"substeps_created": created}

    def _author(self, step, substeps):
        created = 0
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
                    "requires_signature": ss.get("requires_signature", False),
                    "is_inspection_point": ss.get("is_inspection_point", False),
                    # BATCH-scope substeps run once per load (BatchExecution);
                    # default SAMPLED runs per part.
                    "scope": ss.get("scope", SubstepScope.SAMPLED),
                },
            )
            created += 1
        return created

    def _receiving_content(self, recv_step):
        """Receiving inspection (Flow A): the RECEIVING_COMPLETION adapter runs it,
        unit-by-unit capture, then a verdict, then accept or reject."""
        name = recv_step.name
        return {name: [
            {
                "title": "Inspect incoming material",
                "order": 0,
                "is_inspection_point": True,
                "body": _doc(
                    _heading("Incoming inspection"),
                    _para("Inspect the sampled units against the receiving characteristics, then set the verdict."),
                    _callout("note", "Sample size and accept/reject come from the receiving sampling plan (C=0 / AQL)."),
                    _scan(name, "lot-scan", "Scan the lot / packing slip", required=False),
                    *_step_measures(recv_step, name, characteristic="RCV-01"),
                    _quality_status(name, "recv-result", "Incoming inspection result"),
                    _inspection_signatures(name, "recv-signoff", require_detected=True),
                    _error_types(name, "recv-defects", "Defects found", min_rows=0),
                ),
            },
        ]}

    def _reman_content(self, md, model_id, osp_step=None):
        """Remanufacture: step name -> substeps. Built at seed time so measurement
        and 3D-model ids are the real seeded rows."""

        def maybe_measure(step, key, label, characteristic=""):
            """Measurement node only if the demo definition exists."""
            m = md.get(("reman", label))
            return [_measurement(step, key, m, characteristic)] if m else []

        callout_block = (
            [
                _part_callout(
                    "Nozzle inspection points",
                    model_id,
                    [
                        _callout_point("Nozzle Inspection", 1, -0.286, -0.134, 1.042, "Nozzle tip - check for scoring/erosion"),
                        _callout_point("Nozzle Inspection", 2, 0.471, -0.308, 0.595, "Spray-hole bank - verify all holes clear"),
                        _callout_point("Nozzle Inspection", 3, 0.300, -0.184, 0.616, "Seat face - inspect for pitting"),
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
                        _callout("note", "Cores arrive as-is from the field - record what you see, don't clean yet."),
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
                        _callout("caution", "When in doubt, grade down - a reused-but-marginal component fails downstream."),
                        *maybe_measure("Component Grading", "body-bore", "Body Bore Diameter", characteristic="CG-01"),
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
                        # Strict: every component the disassembly BOM expects is graded or
                        # marked missing — the grades resolve the rebuild's scope.
                        _reman_capture("harvestedComponentCapture", "Disassembly", "harvest",
                                       "Grade each component as it comes out",
                                       enumerate_from="disassembly_bom", manual_component_types=[],
                                       strict_enumeration=True),
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
                        _heading("Ultrasonic clean - whole load"),
                        _callout("note", "One cycle cleans the entire basket; the result applies to every part in the load."),
                        # Cycle-level reading: bath temp is measured once for the
                        # load. Binds to the BatchExecution (StepExecutionMeasurement
                        # + a batch QualityReport), not to any one part.
                        *maybe_measure("Cleaning", "bath-temp", "Bath Temperature"),
                        _attest_confirm("Cleaning", "cycle-done", "Cycle complete", "Confirm the wash and rinse cycle finished and the basket was inspected."),
                        # Releasing the cycle signs for the whole load, once:
                        # a signature block in a BATCH substep is signed against
                        # the load, not once per part in it.
                        _attest_signature("Cleaning", "cycle-release",
                                          "Cycle release"),
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
                        _callout("caution", "Handle the nozzle tip with lint-free gloves - fingerprints etch the seat."),
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
                    "body": _doc(
                        _para("Mount the nozzle on the spray rig and record the measured spray angle."),
                        *maybe_measure("Nozzle Inspection", "spray-angle", "Spray Angle", characteristic="N-12"),
                        _attest_signature("Nozzle Inspection", "signoff", "Inspector sign-off"),
                    ),
                },
                {
                    "title": "Report a component found worse",
                    "order": 2,
                    # Only when a reused component fails here. Recording proposes a
                    # change to the rebuild's scope; a lead applies or dismisses it.
                    "is_optional": True,
                    "body": _doc(
                        _para("If a component teardown graded as reusable fails here, record it. A repair this check pre-approves applies at once and the unit goes down that branch; anything else waits here for a lead."),
                        _reman_capture("rebuildFindingCapture", "Nozzle Inspection", "finding",
                                       "Component found worse", required=False),
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
            "Reassembly": [
                {
                    "title": "Reassemble and torque",
                    "order": 0,
                    "is_critical": True,
                    "body": _doc(
                        _para("Reassemble the injector with new seals, then torque the retaining nut to spec."),
                        _callout("caution", "Torque is safety-critical - use the calibrated wrench and the recorded value."),
                        *maybe_measure("Reassembly", "torque", "Reassembly Torque", characteristic="A-01"),
                        _attest_confirm(
                            "Reassembly",
                            "new-seals",
                            "New seals installed",
                            "I confirm new seals were used (no reused seals).",
                        ),
                    ),
                },
                {
                    "title": "Record the components fitted",
                    "order": 1,
                    "body": _doc(
                        _para("Record each component fitted to the rebuilt core, against its rebuild plan."),
                        _callout("note", "Repair-and-return units take back only their own components."),
                        _reman_capture("componentInstallCapture", "Reassembly", "install", "Components fitted"),
                    ),
                },
            ],
            "Final Test": [
                {
                    "title": "Final leak / pressure test",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Pressurize and hold; record the leak-test pressure and the pass/fail result."),
                        *maybe_measure("Final Test", "leak-pressure", "Leak Test Pressure", characteristic="FT-07"),
                        _quality_status("Final Test", "final-result", "Final test result"),
                        _attest_signature("Final Test", "release-signoff", "Release sign-off"),
                    ),
                },
            ],
            "Packaging": [
                {
                    "title": "Pack the rebuilt unit",
                    "order": 0,
                    "body": _doc(
                        _para("Fit the inlet and nozzle caps, bag the unit with its test record, and box it."),
                        _callout("note", "A repair-and-return unit goes back in its owner's packaging, with their reference on the label."),
                        _scan("Packaging", "pack-scan", "Scan the unit's serial"),
                        _attest_confirm("Packaging", "caps", "Caps fitted", "I confirm the inlet and nozzle caps are fitted."),
                    ),
                },
            ],
            # A unit that failed a test is repaired here, then re-enters Nozzle
            # Inspection. The repair is inspected before it leaves, so the record says
            # what was wrong, what was done and who accepted it.
            # Repair nodes (seed/demo/manufacturing DEMO_REPAIR_BRANCHES): a unit comes
            # here only when its nozzle's repair code is raised, then rejoins at Flow
            # Testing, which proves the repair worked.
            "Nozzle Recondition": [
                {
                    "title": "Recondition the nozzle",
                    "order": 0,
                    "body": _doc(
                        _para("Lap the nozzle seat and clear each spray hole. This unit is here because its nozzle was graded for reconditioning."),
                        _callout("note", "Flow Testing comes next and proves the repair - you don't test it here."),
                        _photo("Nozzle Recondition", "seat-after", "Seat face after lapping"),
                        _attest_confirm(
                            "Nozzle Recondition",
                            "holes-clear",
                            "Spray holes clear",
                            "I confirm the seat is lapped and every spray hole is clear.",
                        ),
                    ),
                },
            ],
            "Nozzle Replacement": [
                {
                    "title": "Fit a replacement nozzle",
                    "order": 0,
                    "is_critical": True,
                    "body": _doc(
                        _para("Fit a new nozzle assembly in place of the scrapped one. Scan the replacement so its lot is traced to this unit."),
                        _scan("Nozzle Replacement", "new-nozzle", "Scan the replacement nozzle"),
                        _attest_confirm(
                            "Nozzle Replacement",
                            "fitted",
                            "Replacement fitted",
                            "I confirm the replacement nozzle is seated and the old one is tagged for scrap.",
                        ),
                    ),
                },
            ],
            "Rework": [
                {
                    "title": "Repair and inspect the rework",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Repair the failure recorded on the NCR, then inspect the repair before the unit goes back to inspection."),
                        _callout("note", "Work to the disposition's rework instruction. Anything beyond it needs a new disposition."),
                        _error_types("Rework", "rework-defects", "Defects corrected", required=True, min_rows=1),
                        _photo("Rework", "rework-photo", "Photograph the repaired area", required=False),
                        _quality_status("Rework", "rework-result", "Rework inspection result"),
                        _inspection_signatures("Rework", "rework-signoff", require_detected=True),
                    ),
                },
            ],
        }

        if osp_step is not None:
            content[osp_step.name] = _return_inspection(osp_step, osp_step.name)

        return content

    def _build_content(self, md, model_id, osp_step=None):
        """New manufacture: step name -> substeps. Node ids are keyed `build:<step>`
        so the steps whose names the reman route also uses (Final Test, Rework,
        Nitride Coating) get their own."""

        def b(name):
            return f"build:{name}"

        def maybe_measure(step, key, label, characteristic=""):
            m = md.get(("build", label))
            return [_measurement(b(step), key, m, characteristic)] if m else []

        callouts = (
            [
                _part_callout(
                    "Body inspection points",
                    model_id,
                    [
                        _callout_point(b("Body Inspection"), 1, 0.300, -0.184, 0.616, "Valve seat - check the ground finish"),
                        _callout_point(b("Body Inspection"), 2, 0.471, -0.308, 0.595, "Bore entry - burrs or chatter marks"),
                        _callout_point(b("Body Inspection"), 3, -0.286, -0.134, 1.042, "Body OD - porosity or tool marks"),
                    ],
                )
            ]
            if model_id
            else []
        )

        content = {
            "Machining": [
                {
                    "title": "Turn the injector body",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Load bar stock, run the body program, and measure the first body off the lathe and every tenth after."),
                        _callout("caution", "Bore out of tolerance stops the lot - don't run on while you adjust offsets."),
                        *maybe_measure("Machining", "body-od", "Body OD", characteristic="MC-01"),
                        _quality_status(b("Machining"), "machining-result", "Body result"),
                    ),
                },
            ],
            "Precision Grinding": [
                {
                    "title": "Grind the bore and seat",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Finish-grind the bore and the valve seat, then measure the seat bore."),
                        _callout("caution", "Dress the wheel at the start of the shift and after any reading near the limit."),
                        *maybe_measure("Precision Grinding", "seat-bore", "Seat Bore Diameter", characteristic="PG-02"),
                        _quality_status(b("Precision Grinding"), "grind-result", "Grind result"),
                    ),
                },
            ],
            "Wash": [
                {
                    "title": "Load bodies into the washer",
                    "order": 0,
                    "body": _doc(
                        _para("Scan each body as you load it into the ultrasonic basket. Every body in this load is washed together."),
                        _scan(b("Wash"), "load-scan", "Scan each body into the load"),
                    ),
                },
                {
                    "title": "Run ultrasonic wash cycle",
                    "order": 1,
                    # BATCH scope: one cycle washes the whole basket, so the capture
                    # binds to the load's BatchExecution, not per part.
                    "scope": SubstepScope.BATCH,
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Ultrasonic wash - whole load"),
                        _callout("note", "One cycle washes the entire basket; the result applies to every body in the load."),
                        *maybe_measure("Wash", "bath-temp", "Bath Temperature"),
                        _attest_confirm(b("Wash"), "cycle-done", "Cycle complete", "Confirm the wash and rinse cycle finished and the basket was inspected."),
                        _attest_signature(b("Wash"), "cycle-release", "Cycle release"),
                    ),
                },
            ],
            "Body Inspection": [
                {
                    "title": "Visual body inspection",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _heading("Inspect the finished body"),
                        _callout("caution", "Handle the body by its ends - fingerprints on the seat etch after nitriding."),
                        *callouts,
                        _part_annotation(b("Body Inspection"), "defects", "Mark any defects you find on the model", model_id),
                        _quality_status(b("Body Inspection"), "visual-result", "Visual inspection result"),
                        _equipment_roles(b("Body Inspection"), "equipment"),
                        _inspection_signatures(b("Body Inspection"), "signoff-sig"),
                        _error_types(b("Body Inspection"), "defect-types"),
                    ),
                },
                {
                    "title": "Measure the bore",
                    "order": 1,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Run the bore program on the CMM and record the bore diameter."),
                        *maybe_measure("Body Inspection", "bore", "Bore Diameter", characteristic="BI-03"),
                        _attest_signature(b("Body Inspection"), "signoff", "Inspector sign-off"),
                    ),
                },
            ],
            "Assembly": [
                {
                    "title": "Assemble and torque",
                    "order": 0,
                    "is_critical": True,
                    "body": _doc(
                        _para("Fit the purchased nozzle, control valve and solenoid to the body with new seals, then torque the retaining nut to spec."),
                        _callout("caution", "Torque is safety-critical - use the calibrated wrench and the recorded value."),
                        _scan(b("Assembly"), "nozzle-lot", "Scan the nozzle's lot label"),
                        *maybe_measure("Assembly", "torque", "Assembly Torque", characteristic="A-01"),
                        _attest_confirm(b("Assembly"), "new-seals", "New seals installed", "I confirm new seals were used."),
                    ),
                },
            ],
            "Flow Calibration": [
                {
                    "title": "Calibrate and verify delivery",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Run the calibration cycle on the flow bench, set delivery, and record the flow rate at rated pressure."),
                        _scan(b("Flow Calibration"), "part-scan", "Scan the part barcode"),
                        *maybe_measure("Flow Calibration", "flow-rate", "Flow Rate", characteristic="F-04"),
                        _attest_confirm(b("Flow Calibration"), "bench-confirm", "Flow bench in-calibration",
                                        "I confirm the flow bench calibration is current."),
                    ),
                },
                {
                    "title": "Check the spray",
                    "order": 1,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Fire the injector on the spray rig and record the spray angle."),
                        *maybe_measure("Flow Calibration", "spray-angle", "Spray Angle", characteristic="N-12"),
                        _attest_signature(b("Flow Calibration"), "signoff", "Calibration sign-off"),
                    ),
                },
            ],
            "Final Test": [
                {
                    "title": "Final leak / pressure test",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Pressurize and hold; record the leak-test pressure and the pass/fail result."),
                        *maybe_measure("Final Test", "leak-pressure", "Leak Test Pressure", characteristic="FT-07"),
                        _quality_status(b("Final Test"), "final-result", "Final test result"),
                        _attest_signature(b("Final Test"), "release-signoff", "Release sign-off"),
                    ),
                },
            ],
            "Marking & Packaging": [
                {
                    "title": "Mark and pack",
                    "order": 0,
                    "body": _doc(
                        _para("Laser-mark the serial on the body, check it reads, and pack the injector with its caps fitted."),
                        _scan(b("Marking & Packaging"), "mark-scan", "Scan the laser-marked serial"),
                        _attest_confirm(b("Marking & Packaging"), "caps", "Caps fitted", "I confirm the inlet and nozzle caps are fitted."),
                    ),
                },
            ],
            # A unit that failed a check is repaired here, then re-enters Body Inspection.
            "Rework": [
                {
                    "title": "Repair and inspect the rework",
                    "order": 0,
                    "is_inspection_point": True,
                    "body": _doc(
                        _para("Repair the failure recorded on the NCR, then inspect the repair before the unit goes back to inspection."),
                        _callout("note", "Work to the disposition's rework instruction. Anything beyond it needs a new disposition."),
                        _error_types(b("Rework"), "rework-defects", "Defects corrected", required=True, min_rows=1),
                        _photo(b("Rework"), "rework-photo", "Photograph the repaired area", required=False),
                        _quality_status(b("Rework"), "rework-result", "Rework inspection result"),
                        _inspection_signatures(b("Rework"), "rework-signoff", require_detected=True),
                    ),
                },
            ],
        }
        if osp_step is not None:
            content[osp_step.name] = _return_inspection(osp_step, b(osp_step.name))
        return content
