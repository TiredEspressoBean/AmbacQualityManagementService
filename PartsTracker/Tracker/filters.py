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

    order = django_filters.ModelChoiceFilter(queryset=Orders.objects.none())
    step = django_filters.ModelChoiceFilter(queryset=Steps.objects.none())
    part_type = django_filters.ModelChoiceFilter(queryset=PartTypes.objects.none())
    work_order = django_filters.ModelChoiceFilter(queryset=WorkOrder.objects.none())
    requires_sampling = django_filters.BooleanFilter()

    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    ERP_id = django_filters.CharFilter(lookup_expr="icontains")

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
            "ERP_id", "status__in"
        ]

class OrderFilter(TenantFilterMixin, django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr='icontains')
    archived = django_filters.BooleanFilter()

    customer = django_filters.ModelChoiceFilter(queryset=User.objects.none())
    company = django_filters.ModelChoiceFilter(queryset=Companies.objects.none())

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
        - Local orders (no hubspot_deal_id) are always included
        - HubSpot orders are only included if their current gate starts with 'Gate'
          (indicating they're active in the pipeline, not lost/dropped)
        """
        if value:
            return queryset.filter(
                Q(hubspot_deal_id__isnull=True) |
                Q(hubspot_deal_id='') |
                Q(current_hubspot_gate__stage_name__startswith='Gate')
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

    parent_company = django_filters.ModelChoiceFilter(queryset=Companies.objects.none())

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
            "is_staff", "is_active", "archived",
            "parent_company",
            "date_joined__gte", "date_joined__lte"
        ]
