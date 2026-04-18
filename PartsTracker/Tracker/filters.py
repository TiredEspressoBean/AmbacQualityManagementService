from django_filters import BaseInFilter, CharFilter
from django_filters.widgets import QueryArrayWidget
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.db.models import Q
import django_filters

from .models import Parts, Orders, Steps, PartTypes, WorkOrder, User, Companies


class CharInFilter(BaseInFilter, CharFilter):
    pass


class TenantFilterMixin:
    """
    Mixin that provides tenant-scoped querysets for ModelChoiceFilters.

    Filters the queryset based on the request's tenant context.
    """

    def get_tenant(self):
        """Get tenant from request context."""
        request = getattr(self, 'request', None)
        if request:
            return getattr(request, 'tenant', None)
        return None

    def filter_by_tenant(self, queryset):
        """Filter queryset by current tenant."""
        tenant = self.get_tenant()
        if tenant and hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=tenant)
        return queryset

class PartFilter(TenantFilterMixin, django_filters.FilterSet):
    status__in = CharInFilter(
        field_name="part_status",
        lookup_expr="in",
        widget=QueryArrayWidget(),
    )

    archived = django_filters.BooleanFilter()

    # Module-level ModelChoiceFilter querysets use `unscoped` so import
    # doesn't trip SecureManager (no tenant context at import time). The
    # runtime queryset is set per-request in __init__ via filter_by_tenant,
    # which does tenant-scope via the user's current tenant.
    order = django_filters.ModelChoiceFilter(queryset=Orders.unscoped.none())
    step = django_filters.ModelChoiceFilter(queryset=Steps.unscoped.none())
    part_type = django_filters.ModelChoiceFilter(queryset=PartTypes.unscoped.none())
    work_order = django_filters.ModelChoiceFilter(queryset=WorkOrder.unscoped.none())
    requires_sampling = django_filters.BooleanFilter()

    # Filter for parts that need QA (require sampling but don't have a PASS report)
    needs_qa = django_filters.BooleanFilter(method='filter_needs_qa')

    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    ERP_id = django_filters.CharFilter(lookup_expr="icontains")

    def filter_needs_qa(self, queryset, name, value):
        """
        Filter parts that need QA inspection.

        This queryset filter mirrors the Parts.needs_qa property logic:
        - True = requires_sampling but no PASS QA report (needs inspection)
        - False = has at least one PASS QA report (QA completed)

        See Parts.needs_qa and Parts.qa_completed properties for the single
        source of truth on QA status semantics.
        """
        if value is True:
            # Parts that require sampling but don't have any PASS QA report
            return queryset.filter(requires_sampling=True).exclude(
                error_reports__status='PASS'
            )
        elif value is False:
            # Parts that have at least one PASS QA report (QA completed)
            return queryset.filter(
                requires_sampling=True,
                error_reports__status='PASS'
            ).distinct()
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply tenant filtering to ModelChoiceFilter querysets
        self.filters['order'].queryset = self.filter_by_tenant(Orders.objects.all())
        self.filters['step'].queryset = self.filter_by_tenant(Steps.objects.all())
        self.filters['part_type'].queryset = self.filter_by_tenant(PartTypes.objects.all())
        self.filters['work_order'].queryset = self.filter_by_tenant(WorkOrder.objects.all())

    class Meta:
        model = Parts
        fields = [
            "archived", "requires_sampling",
            "order", "step", "part_type", "work_order",
            "created_at__gte", "created_at__lte",
            "ERP_id", "status__in", "needs_qa"
        ]

class OrderFilter(TenantFilterMixin, django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr='icontains')
    archived = django_filters.BooleanFilter()

    customer = django_filters.ModelChoiceFilter(queryset=User.objects.none())  # User isn't SecureModel; default manager is safe
    company = django_filters.ModelChoiceFilter(queryset=Companies.unscoped.none())

    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')

    estimated_completion__gte = django_filters.DateTimeFilter(field_name="estimated_completion", lookup_expr='gte')
    estimated_completion__lte = django_filters.DateTimeFilter(field_name="estimated_completion", lookup_expr='lte')

    active_pipeline = django_filters.BooleanFilter(method='filter_active_pipeline')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply tenant filtering to ModelChoiceFilter querysets
        self.filters['customer'].queryset = self.filter_by_tenant(
            User.objects.filter(groups__name='Customer')
        )
        self.filters['company'].queryset = self.filter_by_tenant(Companies.objects.all())

    def filter_active_pipeline(self, queryset, name, value):
        """
        Filter to show only actionable orders:
        - Orders with no milestone set are always included (local orders)
        - Orders with a milestone are included only if the milestone is active
          (is_active=True, meaning in-progress, not closed/tabled/completed)

        Uses native Milestone.is_active flag. Falls back to legacy HubSpot filter
        for orders that only have current_hubspot_gate set (transition period).
        """
        if value:
            return queryset.filter(
                Q(current_milestone__isnull=True, hubspot_deal_id__isnull=True) |
                Q(current_milestone__isnull=True, hubspot_deal_id='') |
                Q(current_milestone__is_active=True) |
                # Legacy fallback: orders with HubSpot gate but no milestone yet
                Q(current_milestone__isnull=True, current_hubspot_gate__stage_name__startswith='Gate')
            )
        return queryset

    class Meta:
        model = Orders
        fields = [
            'status', 'archived',
            'customer', 'company', 'created_at__gte', 'created_at__lte',
            'estimated_completion__gte', 'estimated_completion__lte',
            'active_pipeline'
        ]


class UserFilter(TenantFilterMixin, django_filters.FilterSet):
    """Filter for User model"""
    username = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    is_staff = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    archived = django_filters.BooleanFilter()
    user_type = django_filters.ChoiceFilter(choices=User.UserType.choices)

    parent_company = django_filters.ModelChoiceFilter(queryset=Companies.unscoped.none())

    date_joined__gte = django_filters.DateTimeFilter(field_name="date_joined", lookup_expr="gte")
    date_joined__lte = django_filters.DateTimeFilter(field_name="date_joined", lookup_expr="lte")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply tenant filtering to ModelChoiceFilter querysets
        self.filters['parent_company'].queryset = self.filter_by_tenant(Companies.objects.all())

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "is_staff", "is_active", "archived", "user_type",
            "parent_company",
            "date_joined__gte", "date_joined__lte"
        ]
