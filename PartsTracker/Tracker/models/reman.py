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

from .core import SecureModel, User, Companies


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

    CORE_STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('IN_DISASSEMBLY', 'In Disassembly'),
        ('DISASSEMBLED', 'Disassembled'),
        ('SCRAPPED', 'Scrapped'),
    ]

    # Identification
    core_number = models.CharField(
        max_length=100,
        help_text="Unique identifier for this core unit (unique per tenant)"
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
