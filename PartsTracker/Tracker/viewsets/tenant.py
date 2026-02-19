"""
Tenant-related API endpoints.

Provides:
- /api/tenant/current/ - Get current tenant info and deployment mode
- /api/tenant/settings/ - Get/update tenant settings (tenant admin)
- /api/tenants/ - CRUD for platform admins (SaaS mode)
- /api/tenants/signup/ - Self-service tenant creation (SaaS mode)
"""

from drf_spectacular.utils import extend_schema, extend_schema_field, inline_serializer, OpenApiParameter
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class TenantInfoSerializer(serializers.Serializer):
    """Serializer for current tenant information."""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    tier = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_demo = serializers.BooleanField(read_only=True)
    trial_ends_at = serializers.DateTimeField(read_only=True, allow_null=True)
    logo_url = serializers.CharField(read_only=True, allow_null=True)
    primary_color = serializers.CharField(read_only=True, allow_null=True)
    secondary_color = serializers.CharField(read_only=True, allow_null=True)
    contact_email = serializers.EmailField(read_only=True, allow_blank=True, allow_null=True)
    contact_phone = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    website = serializers.URLField(read_only=True, allow_blank=True, allow_null=True)
    address = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    default_timezone = serializers.CharField(read_only=True)


class DeploymentInfoSerializer(serializers.Serializer):
    """Serializer for deployment mode information."""
    mode = serializers.ChoiceField(choices=['saas', 'dedicated'], read_only=True)
    is_saas = serializers.BooleanField(read_only=True)
    is_dedicated = serializers.BooleanField(read_only=True)


class CurrentTenantResponseSerializer(serializers.Serializer):
    """Response serializer for /api/tenant/current/."""
    tenant = TenantInfoSerializer(read_only=True, allow_null=True)
    deployment = DeploymentInfoSerializer(read_only=True)
    features = serializers.DictField(read_only=True)
    limits = serializers.DictField(read_only=True, allow_null=True)
    user = serializers.DictField(read_only=True, allow_null=True)


class CurrentTenantView(APIView):
    """
    Get current tenant information and deployment mode.

    This endpoint is used by the frontend to:
    - Determine which UI elements to show based on deployment mode
    - Get tenant branding (logo, colors)
    - Check feature flags and limits
    - Display tenant name in header

    Authentication is optional - unauthenticated requests get deployment info only.
    """
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CurrentTenantResponseSerializer})
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        user = request.user if request.user.is_authenticated else None

        # Deployment info (always available)
        deployment = {
            'mode': getattr(django_settings, 'DEPLOYMENT_MODE', 'dedicated'),
            'is_saas': getattr(django_settings, 'SAAS_MODE', False),
            'is_dedicated': getattr(django_settings, 'DEDICATED_MODE', True),
        }

        # Tenant info (if resolved)
        tenant_info = None
        if tenant:
            branding = tenant.settings.get('branding', {})
            # Prefer logo field over branding.logo_url
            logo_url = None
            if tenant.logo:
                logo_url = request.build_absolute_uri(tenant.logo.url)
            elif branding.get('logo_url'):
                logo_url = branding.get('logo_url')

            tenant_info = {
                'id': str(tenant.id),
                'name': tenant.name,
                'slug': tenant.slug,
                'tier': tenant.tier,
                'status': tenant.status,
                'is_demo': tenant.is_demo,
                'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
                'logo_url': logo_url,
                'primary_color': branding.get('primary_color'),
                'secondary_color': branding.get('secondary_color'),
                'contact_email': tenant.contact_email or None,
                'contact_phone': tenant.contact_phone or None,
                'website': tenant.website or None,
                'address': tenant.address or None,
                'default_timezone': tenant.default_timezone,
            }

        # Features based on tier (simplified for now)
        features = self._get_features(tenant)

        # Limits based on tier (simplified for now)
        limits = self._get_limits(tenant)

        # User info (if authenticated)
        user_info = None
        if user:
            user_info = {
                'id': str(user.id),
                'email': user.email,
                'name': user.get_full_name() or user.email,
                'is_staff': user.is_staff,
                'groups': list(user.groups.values_list('name', flat=True)),
            }

        return Response({
            'tenant': tenant_info,
            'deployment': deployment,
            'features': features,
            'limits': limits,
            'user': user_info,
        })

    def _get_features(self, tenant):
        """Get feature flags for the tenant."""
        # Default features (all enabled for now)
        features = {
            'mes_lite': True,
            'quality_reports': True,
            'capa': True,
            'documents': True,
            'approvals': True,
            'spc': True,
            'ai_chat': True,
            'api_access': True,
            'export': True,
            '3d_models': True,
        }

        # Override from tenant settings if present
        if tenant and tenant.settings.get('features'):
            features.update(tenant.settings['features'])

        # Tier-based restrictions (for future use)
        # if tenant and tenant.tier == 'starter':
        #     features['spc'] = False
        #     features['ai_chat'] = False

        return features

    def _get_limits(self, tenant):
        """Get resource limits for the tenant."""
        if not tenant:
            return None

        # Default limits (no limits for now)
        limits = {
            'max_users': None,  # None = unlimited
            'max_storage_gb': None,
            'max_api_calls_per_month': None,
        }

        # Override from tenant settings if present
        if tenant.settings.get('limits'):
            limits.update(tenant.settings['limits'])

        return limits


class TenantSettingsView(APIView):
    """
    Get or update tenant settings.

    Only accessible by tenant admins (users in Admin group).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='TenantSettingsResponse',
            fields={
                'name': serializers.CharField(),
                'tier': serializers.CharField(),
                'status': serializers.CharField(),
                'settings': serializers.DictField(),
                'contact_email': serializers.EmailField(allow_blank=True, allow_null=True),
                'contact_phone': serializers.CharField(allow_blank=True, allow_null=True),
                'website': serializers.URLField(allow_blank=True, allow_null=True),
                'address': serializers.CharField(allow_blank=True, allow_null=True),
                'default_timezone': serializers.CharField(),
                'logo_url': serializers.CharField(allow_null=True),
            }
        )}
    )
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'No tenant context'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user is tenant admin
        if not self._is_tenant_admin(request.user):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        logo_url = None
        if tenant.logo:
            logo_url = request.build_absolute_uri(tenant.logo.url)

        return Response({
            'name': tenant.name,
            'tier': tenant.tier,
            'status': tenant.status,
            'settings': tenant.settings,
            'contact_email': tenant.contact_email or None,
            'contact_phone': tenant.contact_phone or None,
            'website': tenant.website or None,
            'address': tenant.address or None,
            'default_timezone': tenant.default_timezone,
            'logo_url': logo_url,
        })

    @extend_schema(
        request=inline_serializer(
            name='TenantSettingsUpdateRequest',
            fields={
                'name': serializers.CharField(required=False),
                'settings': serializers.DictField(required=False),
                'contact_email': serializers.EmailField(required=False, allow_blank=True, allow_null=True),
                'contact_phone': serializers.CharField(required=False, allow_blank=True, allow_null=True),
                'website': serializers.URLField(required=False, allow_blank=True, allow_null=True),
                'address': serializers.CharField(required=False, allow_blank=True, allow_null=True),
                'default_timezone': serializers.CharField(required=False),
            }
        ),
        responses={200: inline_serializer(
            name='TenantSettingsUpdateResponse',
            fields={
                'name': serializers.CharField(),
                'tier': serializers.CharField(),
                'status': serializers.CharField(),
                'settings': serializers.DictField(),
                'contact_email': serializers.EmailField(allow_blank=True, allow_null=True),
                'contact_phone': serializers.CharField(allow_blank=True, allow_null=True),
                'website': serializers.URLField(allow_blank=True, allow_null=True),
                'address': serializers.CharField(allow_blank=True, allow_null=True),
                'default_timezone': serializers.CharField(),
                'logo_url': serializers.CharField(allow_null=True),
            }
        )}
    )
    def patch(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'detail': 'No tenant context'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user is tenant admin
        if not self._is_tenant_admin(request.user):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update allowed fields
        if 'name' in request.data:
            tenant.name = request.data['name']

        if 'settings' in request.data:
            # Merge settings (don't replace entirely)
            tenant.settings.update(request.data['settings'])

        # Update organization fields
        if 'contact_email' in request.data:
            tenant.contact_email = request.data['contact_email']
        if 'contact_phone' in request.data:
            tenant.contact_phone = request.data['contact_phone']
        if 'website' in request.data:
            tenant.website = request.data['website']
        if 'address' in request.data:
            tenant.address = request.data['address']
        if 'default_timezone' in request.data:
            tenant.default_timezone = request.data['default_timezone']

        tenant.save()

        logo_url = None
        if tenant.logo:
            logo_url = request.build_absolute_uri(tenant.logo.url)

        return Response({
            'name': tenant.name,
            'tier': tenant.tier,
            'status': tenant.status,
            'settings': tenant.settings,
            'contact_email': tenant.contact_email or None,
            'contact_phone': tenant.contact_phone or None,
            'website': tenant.website or None,
            'address': tenant.address or None,
            'default_timezone': tenant.default_timezone,
            'logo_url': logo_url,
        })

    def _is_tenant_admin(self, user):
        """Check if user is a tenant admin via permissions."""
        # Superusers and staff always have access
        if user.is_superuser or user.is_staff:
            return True
        # Check for tenant admin permission (admins have '*' which includes this)
        return user.has_tenant_perm('change_tenantgroup')


class TenantLogoView(APIView):
    """
    Upload or delete tenant logo.

    POST: Upload a new logo (multipart/form-data with 'logo' file field)
    DELETE: Remove the current logo
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _is_tenant_admin(self, user):
        if user.is_superuser or user.is_staff:
            return True
        return user.has_tenant_perm('change_tenantgroup')

    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {'logo': {'type': 'string', 'format': 'binary'}}}},
        responses={200: inline_serializer(
            name='TenantLogoResponse',
            fields={'logo_url': serializers.CharField(allow_null=True)}
        )}
    )
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._is_tenant_admin(request.user):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        logo = request.FILES.get('logo')
        if not logo:
            return Response({'detail': 'No logo file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete old logo if exists
        if tenant.logo:
            tenant.logo.delete(save=False)

        tenant.logo = logo
        tenant.save()

        return Response({
            'logo_url': request.build_absolute_uri(tenant.logo.url)
        })

    @extend_schema(
        responses={200: inline_serializer(
            name='TenantLogoDeleteResponse',
            fields={'logo_url': serializers.CharField(allow_null=True)}
        )}
    )
    def delete(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._is_tenant_admin(request.user):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        if tenant.logo:
            tenant.logo.delete(save=True)

        return Response({'logo_url': None})


# =============================================================================
# TENANT CRUD (Platform Admin)
# =============================================================================

class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model."""
    user_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import Tenant
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'tier', 'status', 'is_active', 'is_demo',
            'trial_ends_at', 'created_at', 'updated_at', 'settings', 'user_count',
            'logo', 'logo_url', 'contact_email', 'contact_phone', 'website',
            'address', 'default_timezone',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_count', 'logo_url']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_user_count(self, obj):
        return User.objects.filter(tenant=obj, is_active=True).count()


class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new tenant with admin user."""
    admin_email = serializers.EmailField(write_only=True)
    admin_password = serializers.CharField(write_only=True, required=False)
    admin_first_name = serializers.CharField(write_only=True, default='Admin')
    admin_last_name = serializers.CharField(write_only=True, default='User')

    class Meta:
        from Tracker.models import Tenant
        model = Tenant
        fields = [
            'name', 'slug', 'tier', 'is_demo',
            'admin_email', 'admin_password', 'admin_first_name', 'admin_last_name'
        ]

    def validate_slug(self, value):
        from Tracker.models import Tenant
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Tenant with this slug already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        from Tracker.models import Tenant

        # Extract admin user data
        admin_email = validated_data.pop('admin_email')
        admin_password = validated_data.pop('admin_password', None)
        admin_first_name = validated_data.pop('admin_first_name', 'Admin')
        admin_last_name = validated_data.pop('admin_last_name', 'User')

        # Create tenant
        tenant = Tenant.objects.create(
            status=Tenant.Status.ACTIVE,
            is_active=True,
            **validated_data
        )

        # Create admin user
        user = User.objects.create_user(
            email=admin_email,
            username=admin_email,
            password=admin_password or User.objects.make_random_password(),
            first_name=admin_first_name,
            last_name=admin_last_name,
            tenant=tenant,
            is_staff=True,
        )

        # Add to Admin group
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        user.groups.add(admin_group)

        return tenant


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenants (platform admin only).

    Only available in SaaS mode and requires superuser/staff.
    """
    serializer_class = TenantSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'

    def get_queryset(self):
        from Tracker.models import Tenant
        return Tenant.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return TenantCreateSerializer
        return TenantSerializer

    @action(detail=True, methods=['post'])
    def suspend(self, request, slug=None):
        """Suspend a tenant."""
        from Tracker.models import Tenant
        tenant = self.get_object()
        tenant.status = Tenant.Status.SUSPENDED
        tenant.status_changed_at = timezone.now()
        tenant.save(update_fields=['status', 'status_changed_at'])
        return Response({'status': 'suspended', 'tenant': tenant.slug})

    @action(detail=True, methods=['post'])
    def activate(self, request, slug=None):
        """Activate a suspended tenant."""
        from Tracker.models import Tenant
        tenant = self.get_object()
        tenant.status = Tenant.Status.ACTIVE
        tenant.status_changed_at = timezone.now()
        tenant.save(update_fields=['status', 'status_changed_at'])
        return Response({'status': 'active', 'tenant': tenant.slug})

    @action(detail=True, methods=['get'])
    def users(self, request, slug=None):
        """List users in a tenant."""
        tenant = self.get_object()
        users = User.objects.filter(tenant=tenant).values(
            'id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined'
        )
        return Response(list(users))


# =============================================================================
# SELF-SERVICE SIGNUP (SaaS)
# =============================================================================

class SignupSerializer(serializers.Serializer):
    """Serializer for self-service tenant signup."""
    # Tenant info
    company_name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(required=False, help_text="Auto-generated from company name if not provided")

    # Admin user info
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)

    def validate_slug(self, value):
        from Tracker.models import Tenant
        if value and Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This organization URL is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        from Tracker.models import Tenant
        from django.utils.text import slugify

        company_name = validated_data['company_name']
        slug = validated_data.get('slug') or slugify(company_name)

        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create tenant
        tenant = Tenant.objects.create(
            name=company_name,
            slug=slug,
            tier=Tenant.Tier.STARTER,
            status=Tenant.Status.ACTIVE,
            is_active=True,
        )

        # Create admin user
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            tenant=tenant,
            is_staff=True,
        )

        # Add to Admin group
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        user.groups.add(admin_group)

        return {
            'tenant': tenant,
            'user': user,
        }


class SignupView(APIView):
    """
    Self-service tenant signup endpoint.

    Creates a new tenant and admin user. Only available in SaaS mode.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=SignupSerializer,
        responses={201: inline_serializer(
            name='SignupResponse',
            fields={
                'message': serializers.CharField(),
                'tenant': serializers.DictField(),
                'user': serializers.DictField(),
            }
        )}
    )
    def post(self, request):
        # Check if signup is enabled
        if not getattr(django_settings, 'SAAS_MODE', False):
            return Response(
                {'detail': 'Self-service signup is not available.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        tenant = result['tenant']
        user = result['user']

        return Response({
            'message': 'Account created successfully',
            'tenant': {
                'id': str(tenant.id),
                'name': tenant.name,
                'slug': tenant.slug,
            },
            'user': {
                'id': str(user.id),
                'email': user.email,
            }
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# TENANT GROUP MANAGEMENT (Tenant Admin Self-Service)
# =============================================================================

class TenantGroupSerializer(serializers.ModelSerializer):
    """Serializer for TenantGroup with permission counts."""
    permission_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    preset_key = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import TenantGroup
        model = TenantGroup
        fields = [
            'id', 'name', 'description', 'is_custom',
            'permission_count', 'member_count', 'preset_key',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_custom']

    @extend_schema_field(serializers.IntegerField())
    def get_permission_count(self, obj) -> int:
        return obj.permissions.count()

    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj) -> int:
        return obj.role_assignments.count()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_preset_key(self, obj) -> str | None:
        """Find matching preset key by name (for non-custom groups)."""
        if obj.is_custom:
            return None
        from Tracker.presets import GROUP_PRESETS
        for key, preset in GROUP_PRESETS.items():
            if preset['name'] == obj.name:
                return key
        return None


class TenantGroupDetailSerializer(TenantGroupSerializer):
    """Detailed serializer including permissions list."""
    permissions = serializers.SerializerMethodField()

    class Meta(TenantGroupSerializer.Meta):
        fields = TenantGroupSerializer.Meta.fields + ['permissions']

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj) -> list[str]:
        return list(obj.permissions.values_list('codename', flat=True))


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole (group membership)."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='company.name', read_only=True, allow_null=True)
    granted_by_name = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import UserRole
        model = UserRole
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'group', 'group_name',
            'facility', 'facility_name',
            'company', 'company_name',
            'granted_at', 'granted_by', 'granted_by_name'
        ]
        read_only_fields = ['id', 'granted_at', 'granted_by', 'granted_by_name']

    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.email

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_granted_by_name(self, obj) -> str | None:
        if obj.granted_by:
            return obj.granted_by.get_full_name() or obj.granted_by.email
        return None


class TenantGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenant groups (TenantGroup).

    Allows tenant admins to:
    - List/create/update/delete groups
    - Manage permissions on groups
    - Manage group membership (UserRoles)
    - Clone groups and create from presets
    """
    serializer_class = TenantGroupSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        from Tracker.models import TenantGroup
        if getattr(self, 'swagger_fake_view', False):
            return TenantGroup.objects.none()

        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantGroup.objects.none()

        return TenantGroup.objects.filter(tenant=tenant).prefetch_related(
            'permissions', 'role_assignments__user'
        ).order_by('name')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenantGroupDetailSerializer
        return TenantGroupSerializer

    def check_admin_permission(self, request):
        """Check if user can manage groups."""
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_tenant_perm('change_tenantgroup')

    def create(self, request, *args, **kwargs):
        if not self.check_admin_permission(request):
            return Response(
                {'detail': 'Permission denied - only admins can create groups'},
                status=status.HTTP_403_FORBIDDEN
            )

        from Tracker.models import TenantGroup
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = TenantGroup.objects.create(
            tenant=tenant,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_custom=True
        )

        return Response(TenantGroupSerializer(group).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not self.check_admin_permission(request):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self.check_admin_permission(request):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        instance = self.get_object()
        if instance.role_assignments.exists():
            return Response(
                {'detail': 'Cannot delete group with members. Remove all members first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Permission Management
    # -------------------------------------------------------------------------

    @action(detail=True, methods=['get', 'put', 'post', 'delete'], url_path='permissions')
    def permissions(self, request, id=None):
        """
        Manage permissions on a group.

        GET: List current permissions
        PUT: Replace all permissions
        POST: Add permissions
        DELETE: Remove permissions
        """
        if not self.check_admin_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        group = self.get_object()
        Permission = self._get_permission_model()

        if request.method == 'GET':
            perms = group.permissions.values('id', 'codename', 'name', 'content_type__app_label')
            return Response(list(perms))

        codenames = request.data.get('permissions', [])
        if not isinstance(codenames, list):
            return Response({'detail': 'permissions must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        perms = Permission.objects.filter(codename__in=codenames)

        if request.method == 'PUT':
            group.permissions.set(perms)
            return Response({'status': 'replaced', 'count': perms.count()})

        elif request.method == 'POST':
            group.permissions.add(*perms)
            return Response({'status': 'added', 'count': perms.count()})

        elif request.method == 'DELETE':
            group.permissions.remove(*perms)
            return Response({'status': 'removed', 'count': perms.count()})

    def _get_permission_model(self):
        from django.contrib.auth.models import Permission
        return Permission

    # -------------------------------------------------------------------------
    # Member Management
    # -------------------------------------------------------------------------

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, id=None):
        """
        Manage group members (UserRoles).

        GET: List members
        POST: Add member (user_id required, facility_id/company_id optional)
        """
        if not self.check_admin_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        group = self.get_object()

        if request.method == 'GET':
            roles = group.role_assignments.select_related('user', 'facility', 'company', 'granted_by')
            serializer = UserRoleSerializer(roles, many=True)
            return Response(serializer.data)

        # POST - add member
        from Tracker.models import UserRole
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, tenant=request.tenant)
        except User.DoesNotExist:
            return Response({'detail': 'User not found in tenant'}, status=status.HTTP_404_NOT_FOUND)

        role, created = UserRole.objects.get_or_create(
            user=user,
            group=group,
            facility_id=request.data.get('facility_id'),
            company_id=request.data.get('company_id'),
            defaults={'granted_by': request.user}
        )

        if not created:
            return Response({'detail': 'User already in group'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserRoleSerializer(role).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[OpenApiParameter(name='user_id', location='path', type=str, description='User UUID to remove')],
        responses={200: inline_serializer(name='RemoveMemberResponse', fields={'status': serializers.CharField()})}
    )
    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, id=None, user_id=None):
        """Remove a user from the group."""
        if not self.check_admin_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        group = self.get_object()
        deleted, _ = group.role_assignments.filter(user_id=user_id).delete()

        if deleted == 0:
            return Response({'detail': 'User not in group'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'status': 'removed'})

    # -------------------------------------------------------------------------
    # Clone & Preset Actions
    # -------------------------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='clone')
    def clone(self, request, id=None):
        """Clone a group with a new name."""
        if not self.check_admin_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        source = self.get_object()
        new_name = request.data.get('name')
        if not new_name:
            return Response({'detail': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        from Tracker.models import TenantGroup
        if TenantGroup.objects.filter(tenant=source.tenant, name=new_name).exists():
            return Response({'detail': 'Group with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)

        new_group = TenantGroup.objects.create(
            tenant=source.tenant,
            name=new_name,
            description=request.data.get('description', source.description),
            is_custom=True
        )
        new_group.permissions.set(source.permissions.all())

        return Response(TenantGroupDetailSerializer(new_group).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='preset-diff')
    def preset_diff(self, request, id=None):
        """
        Compare group permissions against its original preset.

        Returns added/removed permissions vs the preset template.
        """
        group = self.get_object()

        # Find preset
        from Tracker.presets import GROUP_PRESETS
        preset_key = None
        for key, preset in GROUP_PRESETS.items():
            if preset['name'] == group.name:
                preset_key = key
                break

        if not preset_key:
            return Response({
                'preset': None,
                'message': 'No matching preset found (custom group)'
            })

        preset = GROUP_PRESETS[preset_key]
        if preset['permissions'] == '__all__':
            preset_perms = set(self._get_permission_model().objects.values_list('codename', flat=True))
        else:
            preset_perms = set(preset['permissions'])

        current_perms = set(group.permissions.values_list('codename', flat=True))

        return Response({
            'preset': preset_key,
            'preset_name': preset['name'],
            'added': sorted(current_perms - preset_perms),
            'removed': sorted(preset_perms - current_perms),
            'unchanged_count': len(current_perms & preset_perms)
        })

    @action(detail=False, methods=['post'], url_path='from-preset')
    def from_preset(self, request):
        """Create a new group from a preset template."""
        if not self.check_admin_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        preset_key = request.data.get('preset')
        custom_name = request.data.get('name')  # Optional override

        from Tracker.presets import GROUP_PRESETS
        if preset_key not in GROUP_PRESETS:
            return Response(
                {'detail': f'Unknown preset: {preset_key}', 'available': list(GROUP_PRESETS.keys())},
                status=status.HTTP_400_BAD_REQUEST
            )

        preset = GROUP_PRESETS[preset_key]
        name = custom_name or preset['name']

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        from Tracker.models import TenantGroup
        if TenantGroup.objects.filter(tenant=tenant, name=name).exists():
            return Response({'detail': 'Group with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)

        group = TenantGroup.objects.create(
            tenant=tenant,
            name=name,
            description=preset['description'],
            is_custom=bool(custom_name)  # Custom if name was overridden
        )

        # Assign permissions
        Permission = self._get_permission_model()
        if preset['permissions'] == '__all__':
            group.permissions.set(Permission.objects.all())
        else:
            perms = Permission.objects.filter(codename__in=preset['permissions'])
            group.permissions.set(perms)

        return Response(TenantGroupDetailSerializer(group).data, status=status.HTTP_201_CREATED)


# =============================================================================
# PERMISSION LIST (For UI Dropdowns)
# =============================================================================

class PermissionListView(APIView):
    """
    List all available permissions, optionally grouped by category.

    Used by frontend permission picker UI.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='grouped', type=bool, description='Group by category')
        ],
        responses={200: inline_serializer(
            name='PermissionListResponse',
            fields={
                'permissions': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    def get(self, request):
        from django.contrib.auth.models import Permission

        grouped = request.query_params.get('grouped', 'false').lower() == 'true'

        perms = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'codename'
        )

        if not grouped:
            return Response({
                'permissions': list(perms.values('id', 'codename', 'name'))
            })

        # Group by category (content_type app_label + model)
        categories = {}
        for perm in perms:
            # Create category key from model name
            model = perm.content_type.model
            category = self._categorize_permission(model, perm.codename)

            if category not in categories:
                categories[category] = []

            categories[category].append({
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'model': model
            })

        return Response({'categories': categories})

    def _categorize_permission(self, model, codename):
        """Map models to user-friendly categories."""
        category_map = {
            # Core
            'user': 'Users & Access',
            'userinvitation': 'Users & Access',
            'tenantgroup': 'Users & Access',
            'userrole': 'Users & Access',
            'facility': 'Organization',
            'companies': 'Organization',
            # Production
            'orders': 'Production',
            'parts': 'Production',
            'workorder': 'Production',
            'parttypes': 'Production',
            # Process
            'processes': 'Process Management',
            'steps': 'Process Management',
            'processstep': 'Process Management',
            'stepedge': 'Process Management',
            'stepexecution': 'Process Management',
            # Quality
            'qualityreports': 'Quality',
            'qualityerrorslist': 'Quality',
            'quarantinedisposition': 'Quality',
            'capa': 'CAPA',
            'capatasks': 'CAPA',
            'rcarecord': 'CAPA',
            # Documents
            'documents': 'Documents',
            'documenttype': 'Documents',
            'threedmodel': 'Documents',
            # Equipment
            'equipments': 'Equipment',
            'equipmenttype': 'Equipment',
            'calibrationrecord': 'Equipment',
            # Sampling
            'samplingrule': 'Sampling',
            'samplingruleset': 'Sampling',
            # Approvals
            'approvaltemplate': 'Approvals',
            'approvalrequest': 'Approvals',
            'approvalresponse': 'Approvals',
            # Training
            'trainingrecord': 'Training',
            'trainingtype': 'Training',
            # SPC
            'measurementresult': 'SPC & Measurements',
            'measurementdefinition': 'SPC & Measurements',
            'spcbaseline': 'SPC & Measurements',
        }

        return category_map.get(model, 'Other')


# =============================================================================
# PRESET LIST
# =============================================================================

class PresetListView(APIView):
    """List available group presets."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='PresetListResponse',
            fields={
                'presets': serializers.ListField(child=serializers.DictField())
            }
        )}
    )
    def get(self, request):
        from Tracker.presets import GROUP_PRESETS

        presets = [
            {
                'key': key,
                'name': preset['name'],
                'description': preset['description'],
                'permission_count': 'all' if preset['permissions'] == '__all__' else len(preset['permissions'])
            }
            for key, preset in GROUP_PRESETS.items()
        ]

        return Response({'presets': presets})


# =============================================================================
# EFFECTIVE PERMISSIONS (For a User)
# =============================================================================

class EffectivePermissionsView(APIView):
    """
    Get effective permissions for a user (union of all their groups).

    Admins can check any user; regular users can only check themselves.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='EffectivePermissionsResponse',
            fields={
                'user_id': serializers.CharField(),
                'user_email': serializers.CharField(),
                'groups': serializers.ListField(child=serializers.DictField()),
                'effective_permissions': serializers.ListField(child=serializers.CharField()),
                'total_count': serializers.IntegerField()
            }
        )}
    )
    def get(self, request, user_id=None):
        target_user_id = user_id or request.user.id

        # Check permission to view other users
        if str(target_user_id) != str(request.user.id):
            if not (request.user.is_superuser or request.user.is_staff or
                    request.user.has_tenant_perm('view_user')):
                return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get all permissions from all groups
        tenant = getattr(request, 'tenant', None) or target_user.tenant

        from Tracker.models import UserRole
        roles = UserRole.objects.filter(
            user=target_user,
            group__tenant=tenant
        ).select_related('group', 'facility', 'company')

        # Collect permissions
        all_perms = set()
        groups_info = []

        for role in roles:
            perms = set(role.group.permissions.values_list('codename', flat=True))
            all_perms.update(perms)
            groups_info.append({
                'group_id': str(role.group.id),
                'group_name': role.group.name,
                'facility': role.facility.name if role.facility else None,
                'company': role.company.name if role.company else None,
                'permission_count': len(perms)
            })

        return Response({
            'user_id': str(target_user.id),
            'user_email': target_user.email,
            'groups': groups_info,
            'effective_permissions': sorted(all_perms),
            'total_count': len(all_perms)
        })


# =============================================================================
# USER TENANTS (Multi-tenant switching)
# =============================================================================

class UserTenantsView(APIView):
    """
    List all tenants the current user has access to.
    Used for the tenant switcher in the sidebar.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='UserTenantsResponse',
            many=True,
            fields={
                'id': serializers.UUIDField(),
                'name': serializers.CharField(),
                'slug': serializers.CharField(),
                'logo_url': serializers.CharField(allow_null=True),
                'tier': serializers.CharField(),
                'is_current': serializers.BooleanField(),
            }
        )}
    )
    def get(self, request):
        from Tracker.models import Tenant

        user = request.user
        current_tenant = getattr(request, 'tenant', None)

        # Get all tenants this user belongs to
        # Users have a tenant FK, but could also have TenantGroupMembership in other tenants
        tenants = set()

        # Primary tenant
        if user.tenant:
            tenants.add(user.tenant)

        # Additional tenants via group memberships
        from Tracker.models import TenantGroupMembership
        memberships = TenantGroupMembership.objects.filter(
            user=user
        ).select_related('group__tenant')

        for membership in memberships:
            if membership.group.tenant:
                tenants.add(membership.group.tenant)

        # Build response
        result = []
        for tenant in sorted(tenants, key=lambda t: t.name):
            logo_url = None
            if tenant.logo:
                logo_url = request.build_absolute_uri(tenant.logo.url)

            result.append({
                'id': str(tenant.id),
                'name': tenant.name,
                'slug': tenant.slug,
                'logo_url': logo_url,
                'tier': tenant.tier,
                'is_current': current_tenant and str(tenant.id) == str(current_tenant.id),
            })

        return Response(result)


class SwitchTenantView(APIView):
    """
    Switch the current user's active tenant context.
    Stores the selected tenant in the session.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            name='SwitchTenantRequest',
            fields={
                'tenant_id': serializers.UUIDField(),
            }
        ),
        responses={200: inline_serializer(
            name='SwitchTenantResponse',
            fields={
                'success': serializers.BooleanField(),
                'tenant_id': serializers.UUIDField(),
                'tenant_name': serializers.CharField(),
            }
        )}
    )
    def post(self, request):
        from Tracker.models import Tenant, TenantGroupMembership

        tenant_id = request.data.get('tenant_id')
        if not tenant_id:
            return Response(
                {'detail': 'tenant_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {'detail': 'Tenant not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify user has access to this tenant
        user = request.user
        has_access = False

        if user.tenant and str(user.tenant.id) == str(tenant_id):
            has_access = True
        elif TenantGroupMembership.objects.filter(
            user=user,
            group__tenant=tenant
        ).exists():
            has_access = True

        if not has_access:
            return Response(
                {'detail': 'You do not have access to this organization'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Store in session
        request.session['active_tenant_id'] = str(tenant.id)
        request.session.modified = True

        return Response({
            'success': True,
            'tenant_id': str(tenant.id),
            'tenant_name': tenant.name,
        })
