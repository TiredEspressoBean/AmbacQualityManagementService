from django_filters import BaseInFilter, CharFilter
from django_filters.widgets import QueryArrayWidget
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from .models import *
import django_filters


class CharInFilter(BaseInFilter, CharFilter):
    pass

class PartFilter(django_filters.FilterSet):
    status__in = CharInFilter(
        field_name="part_status",
        lookup_expr="in",
        widget=QueryArrayWidget(),
    )

    archived = django_filters.BooleanFilter()

    order = django_filters.ModelChoiceFilter(queryset=Orders.objects.all())
    step = django_filters.ModelChoiceFilter(queryset=Steps.objects.all())
    part_type = django_filters.ModelChoiceFilter(queryset=PartTypes.objects.all())
    work_order = django_filters.ModelChoiceFilter(queryset=WorkOrder.objects.all())
    requires_sampling = django_filters.BooleanFilter()

    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    ERP_id = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Parts
        fields = [
            "archived", "requires_sampling",
            "order", "step", "part_type", "work_order",
            "created_at__gte", "created_at__lte",
            "ERP_id", "status__in"
        ]

class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr='icontains')
    archived = django_filters.BooleanFilter()

    customer = django_filters.ModelChoiceFilter(queryset=User.objects.filter(groups__name='Customer'))
    company = django_filters.ModelChoiceFilter(queryset=Companies.objects.all())

    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')

    estimated_completion__gte = django_filters.DateTimeFilter(field_name="estimated_completion", lookup_expr='gte')
    estimated_completion__lte = django_filters.DateTimeFilter(field_name="estimated_completion", lookup_expr='lte')

    class Meta:
        model = Orders
        fields = [
            'status', 'archived',
            'customer', 'company', 'created_at__gte', 'created_at__lte',
            'estimated_completion__gte', 'estimated_completion__lte'
        ]


class UserFilter(django_filters.FilterSet):
    """Filter for User model"""
    username = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    is_staff = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    archived = django_filters.BooleanFilter()
    
    parent_company = django_filters.ModelChoiceFilter(queryset=Companies.objects.all())
    
    date_joined__gte = django_filters.DateTimeFilter(field_name="date_joined", lookup_expr="gte")
    date_joined__lte = django_filters.DateTimeFilter(field_name="date_joined", lookup_expr="lte")
    
    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "is_staff", "is_active", "archived",
            "parent_company",
            "date_joined__gte", "date_joined__lte"
        ]
