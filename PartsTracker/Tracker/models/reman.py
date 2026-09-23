"""
Remanufacturing Add-on Models

Contains models specific to remanufacturing operations:
- Core: Incoming used unit for remanufacturing
- HarvestedComponent: Component extracted from core during disassembly
- DisassemblyBOMLine: Expected components from disassembling a core type

These models enable tracking of:
- Incoming cores from customers, purchases, or warranty returns
- Components harvested during disassembly
- Core credit management
- Component condition grading and disposition
"""

from django.db import models

from .core import FULFILMENT_MODE_CHOICES, SecureModel, User, Companies


class Core(SecureModel):
    """
    Represents an incoming used unit (core) for remanufacturing.

    Cores are complete units that will be disassembled to harvest usable components.
    Common in automotive (engine blocks, transmissions), aerospace (turbine engines),
    and industrial equipment remanufacturing.

    Lifecycle:
    1. Received - Core arrives and is logged
    2. In Disassembly - Core is being taken apart
    3. Disassembled - All components have been harvested
    4. Scrapped - Core deemed not suitable for disassembly
    """
    CONDITION_GRADE_CHOICES = [
        ('A', 'Grade A - Excellent'),
        ('B', 'Grade B - Good'),
        ('C', 'Grade C - Fair'),
        ('SCRAP', 'Scrap - Not Usable'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('CUSTOMER_RETURN', 'Customer Return'),
        ('PURCHASED', 'Purchased Core'),
        ('WARRANTY', 'Warranty Return'),
        ('TRADE_IN', 'Trade-In'),
    ]

    # Teardown ends in one of exactly two places, and which one is not a separate
    # decision — it follows from `fulfilment_mode`. A unit that goes back to its
    # customer must be rebuilt; anything else is a source of parts. So there is no
    # "what shall we do with it" field: `returns_to_customer` already answers it.
    CORE_STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('IN_DISASSEMBLY', 'In Disassembly'),
        ('DISASSEMBLED', 'Disassembled'),
        # Repair-and-return path: rebuilt on the SAME work order the teardown ran on,
        # so the unit keeps one traceable thread from arrival to shipment.
        ('IN_REBUILD', 'In Rebuild'),
        ('REBUILT', 'Rebuilt — ready to return'),
        # Exchange path: the usable components became stock and the core is consumed.
        ('HARVESTED', 'Harvested to inventory'),
        ('SCRAPPED', 'Scrapped'),
    ]

    # Identification
    core_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Our handle for this unit (unique per tenant). Auto-generated as "
                  "CORE-YYYY-#### when left blank — every other business identifier "
                  "here is (orders, shipments, approvals, quality reports, "
                  "dispositions, qualifications), and cores arrive in batches where "
                  "hand-typing forty unique numbers is both slow and the obvious place "
                  "for a duplicate to creep in. Still writable, for a shop with its own "
                  "tagging scheme. The CUSTOMER's references live elsewhere: "
                  "`source_reference` for an RMA or PO, `serial_number` for the OEM "
                  "serial.",
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Original equipment serial number if available"
    )

    # Type and classification
    core_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='cores',
        help_text="Type of unit (e.g., Fuel Injector, Turbocharger)"
    )

    # Receipt info
    received_date = models.DateField()
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='received_cores'
    )

    # Source tracking
    customer = models.ForeignKey(
        Companies,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='returned_cores',
        help_text="Customer who returned this core"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='CUSTOMER_RETURN'
    )
    source_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="RMA number, PO number, or other reference"
    )

    # Where the unit is GOING, which `source_type` above does not answer — that records
    # where the core came FROM. A customer return can be either: their own unit to repair
    # and send back, or a core surrendered against an exchange.
    #
    # Choices imported from models/core.py, where `Companies` carries the customer's
    # standing arrangement. One definition, so the arrangement and the core's actual
    # mode can never offer different options.
    fulfilment_mode = models.CharField(
        max_length=20,
        choices=FULFILMENT_MODE_CHOICES,
        default='EXCHANGE',
        help_text="Whether this exact unit goes back to the customer, or they receive "
                  "one from stock. Not the same question as source_type, which records "
                  "where the core came from. Drives three things: whether the rebuilt "
                  "unit must keep this core's identity, whether a scope change needs "
                  "the customer's authorisation before work proceeds, and whether "
                  "components harvested from OTHER cores may be built into it.",
    )
    """How this core is fulfilled. Defaults to EXCHANGE because that is the mode with no
    extra obligations — no quoting gate, no serial continuity, free use of the harvest
    pool — so a shop that never configures it gets the simpler behaviour rather than
    silently acquiring a customer-authorisation requirement it does not have."""

    # Condition assessment
    condition_grade = models.CharField(
        max_length=10,
        choices=CONDITION_GRADE_CHOICES,
        help_text="Overall condition grade assigned at receipt"
    )
    condition_notes = models.TextField(
        blank=True,
        help_text="Detailed notes on condition observed at receipt"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=CORE_STATUS_CHOICES,
        default='RECEIVED'
    )
    disassembly_started_at = models.DateTimeField(null=True, blank=True)
    disassembly_completed_at = models.DateTimeField(null=True, blank=True)
    disassembled_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='disassembled_cores'
    )

    # Core credit management
    core_credit_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Credit value to be issued for this core"
    )
    core_credit_issued = models.BooleanField(
        default=False,
        help_text="Whether core credit has been issued to customer"
    )
    core_credit_issued_at = models.DateTimeField(null=True, blank=True)

    # Linked work order (optional - if disassembly is tracked as work order)
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cores'
    )

    # Routing position within the teardown Process (fine-grained, mirrors Parts.step).
    # Core.status stays coarse (RECEIVED/IN_DISASSEMBLY/DISASSEMBLED/SCRAPPED);
    # this field tracks which Op the Core is currently at within the Process graph.
    step = models.ForeignKey(
        'Tracker.Steps',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='active_cores',
        help_text="Current Step in the teardown Process (null for cores not yet routed)."
    )

    class Meta:
        verbose_name = 'Core'
        verbose_name_plural = 'Cores'
        ordering = ['-received_date']
        indexes = [
            models.Index(fields=['core_number']),
            models.Index(fields=['status', 'received_date']),
            models.Index(fields=['customer', 'received_date']),
            models.Index(fields=['core_type', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'core_number'],
                name='core_tenant_number_uniq'
            ),
        ]
        permissions = [
            ('start_disassembly', 'Can start core disassembly'),
            ('complete_disassembly', 'Can complete core disassembly'),
            ('scrap_core', 'Can scrap a core'),
        ]

    def save(self, *args, **kwargs):
        # Auto-fill only; the sequence helper takes a row lock so two clerks receiving
        # at once cannot collide (see utils.sequences.generate_next_sequence). Mirrors
        # Orders.save — this is field auto-fill, not business logic in save().
        if not self.core_number:
            self.core_number = self.generate_core_number(self.tenant)
        super().save(*args, **kwargs)

    @classmethod
    def generate_core_number(cls, tenant=None):
        """Next `CORE-YYYY-####` for this tenant, race-safe."""
        from django.utils import timezone as _tz
        from Tracker.utils.sequences import generate_next_sequence

        return generate_next_sequence(
            queryset=cls.objects,
            number_field='core_number',
            prefix=f"CORE-{_tz.now().year}-",
            padding=4,
            tenant=tenant,
        )

    def __str__(self):
        return f"Core {self.core_number} ({self.core_type.name})"

    def start_disassembly(self, user):
        """Thin wrapper — delegates to `services.reman.core.start_core_disassembly`."""
        from Tracker.services.reman.core import start_core_disassembly
        return start_core_disassembly(self, user)

    def complete_disassembly(self, user):
        """Thin wrapper — delegates to `services.reman.core.complete_core_disassembly`."""
        from Tracker.services.reman.core import complete_core_disassembly
        return complete_core_disassembly(self, user)

    def scrap(self, reason=""):
        """Thin wrapper — delegates to `services.reman.core.scrap_core`."""
        from Tracker.services.reman.core import scrap_core
        return scrap_core(self, reason)

    def issue_credit(self):
        """Thin wrapper — delegates to `services.reman.core.issue_core_credit`."""
        from Tracker.services.reman.core import issue_core_credit
        return issue_core_credit(self)

    # ===== FULFILMENT =====

    @property
    def returns_to_customer(self) -> bool:
        """This exact unit goes back to the customer it came from.

        Expressed once, here, rather than re-derived as `mode == 'REPAIR_RETURN'` at
        each call site: three separate rules key off it (identity, authorisation,
        harvest pooling) and a fourth comparison written slightly differently is how
        they drift apart.
        """
        return self.fulfilment_mode == 'REPAIR_RETURN'

    @property
    def allows_pooled_harvest(self) -> bool:
        """Whether components harvested from OTHER cores may be built into this one.

        False under repair-and-return: the customer's unit keeps its own parts. True for
        an exchange rebuild, where the harvest is stock like any other and the customer
        receives *a* unit rather than theirs.

        What "its own parts" means exactly — every component, or only the serial-bearing
        one — is a customer-commitment question with real cost at the bench, and is
        deliberately not decided here. This answers the coarse question the kit resolver
        needs; a finer rule can narrow it later without moving the concept.
        """
        return not self.returns_to_customer

    @property
    def scope_needs_customer_approval(self) -> bool:
        """Whether findings that widen the rebuild have to be authorised before work.

        Only when the unit is theirs. On an exchange rebuild the shop owns the unit and
        the cost, so scope is an internal planning decision; on repair-and-return a
        wider scope is a bigger bill for someone who has not agreed to it yet — the
        "over-and-above" process every MRO shop runs.

        Nothing consumes this yet: the quoting gate is the repair-and-return half of the
        loop and is not built. It lives here so the rule has one home when it is.
        """
        return self.returns_to_customer

    # ===== WORKFLOW ENGINE METHODS (mirror of Parts) =====

    @property
    def process(self):
        """The teardown Process this Core is routing through (via linked WorkOrder)."""
        return self.work_order.process if self.work_order else None

    def _check_cycle_limit(self, target_step):
        """Mirror of Parts._check_cycle_limit — escalates on max_visits exceeded."""
        from Tracker.models.mes_lite import EdgeType, StepEdge, StepExecution

        if target_step is None or target_step.max_visits is None:
            return target_step

        current_visits = StepExecution.objects.filter(core=self, step=target_step).count()  # tenant-safe: scoped by `core` FK

        if current_visits >= target_step.max_visits:
            process = self.process
            if process:
                escalation_edge = StepEdge.objects.filter(
                    process=process,
                    from_step=target_step,
                    edge_type=EdgeType.ESCALATION,
                ).first()
                if escalation_edge:
                    return escalation_edge.to_step
            return None

        return target_step

    def _get_edge(self, from_step, edge_type):
        """Mirror of Parts._get_edge — looks up StepEdge in the Core's Process."""
        from Tracker.models.mes_lite import StepEdge

        process = self.process
        if not process:
            return None
        edge = StepEdge.objects.filter(
            process=process,
            from_step=from_step,
            edge_type=edge_type,
        ).first()
        return edge.to_step if edge else None

    def get_next_step(self, decision_result=None):
        """Determine the next teardown Step for this Core.

        Mirrors `Parts.get_next_step` but without Parts-specific QualityReport
        lookups: for QA_RESULT decision points, the operator/substep must supply
        `decision_result` explicitly (Cores don't auto-resolve from QualityReport
        history because QualityReport is Parts-scoped).

        Returns:
            Steps instance, or None if terminal/no next step.
        """
        from Tracker.models.mes_lite import (
            DecisionDataMissing,
            EdgeType,
            ProcessStep,
            StepEdge,
        )

        current = self.step
        if not current:
            return None

        if current.is_terminal:
            return None

        if current.is_decision_point:
            if current.decision_type == 'QA_RESULT':
                if decision_result is None:
                    raise DecisionDataMissing(
                        f"decision_result required for qa_result decision at step '{current.name}'"
                    )
                if decision_result == 'PASS':
                    return self._check_cycle_limit(self._get_edge(current, EdgeType.DEFAULT))
                return self._check_cycle_limit(self._get_edge(current, EdgeType.ALTERNATE))

            elif current.decision_type == 'MEASUREMENT':
                process = self.process
                if process:
                    edges = StepEdge.objects.filter(
                        process=process,
                        from_step=current,
                    ).select_related('condition_measurement')

                    for edge in edges:
                        if edge.condition_measurement and edge.condition_value is not None:
                            if decision_result is None:
                                continue
                            threshold = float(edge.condition_value)
                            value = float(decision_result)
                            if edge.condition_operator == 'gte':
                                passed = value >= threshold
                            elif edge.condition_operator == 'lte':
                                passed = value <= threshold
                            else:
                                passed = value == threshold

                            if passed and edge.edge_type == EdgeType.DEFAULT:
                                return self._check_cycle_limit(edge.to_step)
                            elif not passed and edge.edge_type == EdgeType.ALTERNATE:
                                return self._check_cycle_limit(edge.to_step)

                return self._check_cycle_limit(self._get_edge(current, EdgeType.DEFAULT))

            elif current.decision_type == 'MANUAL':
                if decision_result in ('DEFAULT', 'PASS'):
                    return self._check_cycle_limit(self._get_edge(current, EdgeType.DEFAULT))
                elif decision_result in ('ALTERNATE', 'FAIL'):
                    return self._check_cycle_limit(self._get_edge(current, EdgeType.ALTERNATE))
                else:
                    raise ValueError(
                        "Manual decision required: 'DEFAULT'/'PASS' or 'ALTERNATE'/'FAIL'"
                    )

        # Non-decision point: default edge
        default_next = self._get_edge(current, EdgeType.DEFAULT)
        if default_next:
            return self._check_cycle_limit(default_next)

        # Fallback: ProcessStep order
        process = self.process
        if process:
            current_ps = ProcessStep.objects.filter(process=process, step=current).first()
            if current_ps:
                next_ps = ProcessStep.objects.filter(
                    process=process,
                    order=current_ps.order + 1,
                ).first()
                if next_ps:
                    return self._check_cycle_limit(next_ps.step)

        return None

    def advance_step(self, operator=None, decision_result=None):
        """Thin delegate — see `services.mes.cores.advance_core_step`."""
        from Tracker.services.mes.cores import advance_core_step
        return advance_core_step(self, operator=operator, decision_result=decision_result)

    @property
    def harvested_component_count(self):
        """Number of components harvested from this core."""
        return self.harvested_components.count()

    @property
    def usable_component_count(self):
        """Number of harvested components that are usable (not scrapped)."""
        return self.harvested_components.filter(is_scrapped=False).count()


class HarvestedComponent(SecureModel):
    """
    Represents a component extracted from a core during disassembly.

    Harvested components go through condition assessment and either:
    - Become inventory items (linked to Parts model) for reuse
    - Get scrapped if not suitable for reuse

    This enables full traceability from finished reman product back to
    the original core the component came from.
    """
    CONDITION_GRADE_CHOICES = [
        ('A', 'Grade A - Excellent'),
        ('B', 'Grade B - Good'),
        ('C', 'Grade C - Fair'),
        ('SCRAP', 'Scrap - Not Usable'),
    ]

    # Source
    core = models.ForeignKey(
        Core,
        on_delete=models.PROTECT,
        related_name='harvested_components'
    )

    # Component type
    component_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='harvested_as'
    )

    # Linked part (created when component is accepted into inventory)
    component_part = models.OneToOneField(
        'Tracker.Parts',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='harvested_from',
        help_text="The Parts record created for this component (if accepted)"
    )

    # Harvesting info
    disassembled_at = models.DateTimeField(auto_now_add=True)
    disassembled_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='harvested_components'
    )

    # Condition assessment
    condition_grade = models.CharField(
        max_length=10,
        choices=CONDITION_GRADE_CHOICES
    )
    condition_notes = models.TextField(blank=True)

    # Disposition
    is_scrapped = models.BooleanField(default=False)
    scrap_reason = models.CharField(max_length=200, blank=True)
    scrapped_at = models.DateTimeField(null=True, blank=True)
    scrapped_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scrapped_components'
    )

    # Position/identification within core (optional)
    position = models.CharField(
        max_length=50,
        blank=True,
        help_text="Position within core (e.g., 'Cyl 1', 'Position A')"
    )
    original_part_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Original part number if readable"
    )

    class Meta:
        verbose_name = 'Harvested Component'
        verbose_name_plural = 'Harvested Components'
        ordering = ['-disassembled_at']
        indexes = [
            models.Index(fields=['core', 'component_type']),
            models.Index(fields=['condition_grade', 'is_scrapped']),
            models.Index(fields=['component_type', 'is_scrapped']),
        ]
        permissions = [
            ('grade_component', 'Can grade a harvested component'),
            ('accept_component', 'Can accept a harvested component to inventory'),
            ('reject_component', 'Can reject a harvested component'),
        ]

    def __str__(self):
        status = " (scrapped)" if self.is_scrapped else ""
        return f"{self.component_type.name} from Core {self.core.core_number}{status}"

    def scrap(self, user, reason=""):
        """Thin wrapper — delegates to `services.reman.harvested_component.scrap_component`."""
        from Tracker.services.reman.harvested_component import scrap_component
        return scrap_component(self, user, reason=reason)

    def accept_to_inventory(self, user, erp_id=None, transfer_life=True):
        """Thin wrapper — delegates to `services.reman.harvested_component.accept_component_to_inventory`."""
        from Tracker.services.reman.harvested_component import accept_component_to_inventory
        return accept_component_to_inventory(
            self, user, erp_id=erp_id, transfer_life=transfer_life
        )

    def _transfer_life_tracking(self, part):
        """
        Transfer applicable life tracking from Core to the new Part.

        Only transfers tracking where the definition applies to the component_type
        (via PartTypeLifeLimit).
        """
        from .life_tracking import LifeTracking, PartTypeLifeLimit

        # Get life tracking records from the Core
        core_tracking = LifeTracking.objects.for_object(self.core)

        # Get definitions that apply to this component type
        applicable_definitions = set(
            PartTypeLifeLimit.objects.filter(
                part_type=self.component_type
            ).values_list('definition_id', flat=True)
        )

        for ct in core_tracking:
            # Only transfer if this definition applies to the component type
            if ct.definition_id in applicable_definitions:
                LifeTracking.for_object(
                    part,
                    ct.definition,
                    accumulated=ct.accumulated,
                    reference_date=ct.reference_date,
                    source=LifeTracking.Source.TRANSFERRED,
                )


class DisassemblyBOMLine(SecureModel):
    """
    Defines expected components from disassembling a core type.

    This is a "reverse BOM" - instead of defining what goes INTO a product,
    it defines what we expect to get OUT OF a core during disassembly.

    Used for:
    - Setting expectations for disassembly yield
    - Tracking fallout rates by component type
    - Planning component inventory based on expected core volume
    """

    _is_versioned = True  # engineering judgment — reman yield spec

    # The core type being disassembled
    core_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='disassembly_bom_lines',
        help_text="The type of core being disassembled"
    )

    # The component type expected
    component_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='harvested_from_bom',
        help_text="The type of component expected from disassembly"
    )

    # Expected quantities
    expected_qty = models.PositiveIntegerField(
        default=1,
        help_text="Number of this component expected per core"
    )
    expected_fallout_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Expected percentage of components that won't be usable (0.10 = 10%)"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Special handling instructions or notes"
    )

    # Optional ordered position labels (Reman DWI Q4). When populated, the
    # HarvestedComponentCapture node pre-fills each enumerated row's position
    # from positions[row_index]. List length must match expected_qty when both
    # are set. Empty/null = free-text position input (backward compatible).
    positions = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Optional ordered list of position labels (e.g., ['Cyl 1', 'Cyl 2', "
            "'Cyl 3', 'Cyl 4']) of length expected_qty. Pre-fills the capture "
            "node's position field per row. Free-text when empty."
        ),
    )

    # Ordering
    line_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Disassembly BOM Line'
        verbose_name_plural = 'Disassembly BOM Lines'
        ordering = ['core_type', 'line_number']
        constraints = [
            models.UniqueConstraint(
                fields=['core_type', 'component_type'],
                condition=models.Q(is_current_version=True),
                name='disassemblybomline_coretype_component_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.core_type.name} yields {self.expected_qty}x {self.component_type.name}"

    @property
    def expected_usable_qty(self):
        """Expected usable quantity after fallout."""
        return self.expected_qty * (1 - float(self.expected_fallout_rate))


# Which slot resolution a repair code answers. Mirrors the resolutions in
# `services/reman/rebuild.py` — defined here because the model stores them, and
# imported there rather than duplicated.
REPAIR_CODE_TRIGGER_CHOICES = [
    ('RECONDITION', 'When the recovered component needs work before it goes back'),
    ('REPLACE_POOL', 'When the slot is filled from recovered stock'),
    ('REPLACE_BUY', 'When the slot is filled by a purchase'),
    ('REUSE', 'When the recovered component goes back as-is'),
    ('ALWAYS', 'Always — part of the base scope, whatever the finding'),
    # Raised only by a preset that names it. This is what distinguishes one sold
    # rebuild level from another: "Full overhaul" includes codes "Standard rebuild"
    # does not, and no finding raises them on its own.
    ('PRESET', 'Only when a rebuild level includes it'),
]


class RepairCode(SecureModel):
    """Operations a finding adds to a rebuild.

    A repair code is a SLOT RESOLUTION THAT EMITS OPERATIONS, which is the whole
    idea: "recondition the nozzle" and "replace the nozzle" resolve the same slot,
    but one is work and the other is a part. Scope and kit are therefore one
    decision rather than two passes — see `Documents/REMAN_REBUILD_LOOP_DESIGN.md`
    §6.4.

    Codes compose. A core with a worn nozzle and a scored valve gets the union of
    both codes' operations, which is why this is a table of codes rather than a set
    of authored end-to-end routes: N findings would otherwise need 2^N routes.
    """

    _is_versioned = True  # engineering judgment — what work a finding implies

    code = models.CharField(
        max_length=30,
        help_text="Short identifier the shop uses, e.g. NZL-RECON.",
    )
    name = models.CharField(
        max_length=200,
        help_text="What this code does, in the words the bench would use.",
    )
    component_type = models.ForeignKey(
        'Tracker.PartTypes',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='repair_codes',
        help_text="The component this code applies to. Blank means it applies "
                  "whatever the component — for whole-unit work like final test.",
    )
    trigger = models.CharField(
        max_length=20,
        choices=REPAIR_CODE_TRIGGER_CHOICES,
        default='RECONDITION',
        help_text="Which finding raises this code. ALWAYS means it is part of the "
                  "base scope and is not raised by a finding at all.",
    )
    steps = models.ManyToManyField(
        'Tracker.Steps',
        blank=True,
        related_name='repair_codes',
        help_text="Operations this code adds to the rebuild. The unit's scope is "
                  "the union of the operations its raised codes carry.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Repair Code'
        verbose_name_plural = 'Repair Codes'
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                condition=models.Q(is_current_version=True),
                name='repaircode_tenant_code_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class RebuildScopePreset(SecureModel):
    """A named starting scope for rebuilding a core type.

    The ENTRY scope in the two-layer model (§3.3): what was quoted and sold, before
    anything was found. An engine shop sells "performance restoration"; findings
    then extend it. A shop with three rebuild levels authors three presets and never
    opens the code table; a shop with a dozen uses the same mechanism and lets
    findings do the rest.

    Deliberately a set of CODES rather than a set of steps, so a tier is a
    pre-composed selection of the same primitive rather than a second kind of thing.
    """

    _is_versioned = True  # engineering judgment — what a named rebuild level includes

    core_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.CASCADE,
        related_name='rebuild_scope_presets',
        help_text="The core type this preset applies to.",
    )
    name = models.CharField(
        max_length=100,
        help_text="What the shop sells this as, e.g. 'Standard rebuild'.",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Proposed automatically when a rebuild is planned for this core "
                  "type. At most one per core type.",
    )
    codes = models.ManyToManyField(
        RepairCode,
        blank=True,
        related_name='presets',
        help_text="The codes this level includes before any finding is applied.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Rebuild Scope Preset'
        verbose_name_plural = 'Rebuild Scope Presets'
        ordering = ['core_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'core_type', 'name'],
                condition=models.Q(is_current_version=True),
                name='rebuildscopepreset_tenant_coretype_name_uniq',
            ),
            # One default per core type. Partial index rather than validation, so two
            # concurrent writers cannot both win — the same reason the versioning
            # constraints above are DB-level.
            models.UniqueConstraint(
                fields=['tenant', 'core_type'],
                condition=models.Q(is_default=True, is_current_version=True),
                name='rebuildscopepreset_one_default_per_coretype',
            ),
        ]

    def __str__(self):
        return f"{self.core_type.name}: {self.name}"


# How a rebuild slot gets filled. Lives here because `RebuildSlotOverride` stores it;
# `services/reman/rebuild.py` imports these rather than keeping a second copy, which is
# how the two would otherwise drift.
SLOT_RESOLUTION_CHOICES = [
    ('REUSE', 'Reuse as-is — the recovered component is serviceable'),
    ('RECONDITION', 'Recondition — work it before it goes back'),
    ('REPLACE_POOL', 'Replace from recovered stock'),
    ('REPLACE_BUY', 'Replace with a purchase'),
]


class RebuildSlotOverride(SecureModel):
    """A planner's decision that differs from the proposed one.

    Stores the DEVIATION, not the slot. The proposal is derived from findings and is
    cheap to recompute, so persisting every slot would mean storing thirty rows a unit
    that mostly agree with the computation — a guess written down as though it were a
    record. What is worth keeping is where a person disagreed, and why.

    `reason` is required for that reason: an override with no reason is indistinguishable
    from a misclick six months later, and this is the row an auditor reads when asking
    why a unit was built the way it was.
    """

    core = models.ForeignKey(
        Core,
        on_delete=models.CASCADE,
        related_name='slot_overrides',
        help_text="The core whose rebuild plan this overrides.",
    )
    bom_line = models.ForeignKey(
        'Tracker.BOMLine',
        on_delete=models.CASCADE,
        related_name='rebuild_slot_overrides',
        help_text="The assembly BOM line the slot came from.",
    )
    position = models.CharField(
        max_length=50,
        blank=True,
        help_text="Which slot on that line — blank for an unpositioned one. Blank rather "
                  "than null on purpose: a unique constraint over a nullable column stops "
                  "preventing anything in Postgres.",
    )
    resolution = models.CharField(
        max_length=20,
        choices=SLOT_RESOLUTION_CHOICES,
        help_text="What the planner decided instead.",
    )
    reason = models.TextField(
        help_text="Why the proposal was wrong. Required — an override without one cannot "
                  "be told from a misclick later, and this is the row that answers why a "
                  "unit was built the way it was.",
    )
    overridden_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='rebuild_slot_overrides',
    )

    class Meta:
        verbose_name = 'Rebuild Slot Override'
        verbose_name_plural = 'Rebuild Slot Overrides'
        ordering = ['core', 'bom_line', 'position']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'core', 'bom_line', 'position'],
                name='rebuildslotoverride_one_per_slot',
            ),
        ]

    def __str__(self):
        where = self.position or 'unpositioned'
        return f"{self.core.core_number} {where}: {self.resolution}"
