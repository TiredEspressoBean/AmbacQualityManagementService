# serializers/dms.py - Document Management System serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import (
    # Core models
    Documents, DocumentType, User,
    # DMS models
    ChatSession,
    # QMS models
    ThreeDModel, HeatMapAnnotations,
    # MES Lite models
    PartTypes, Steps,
)

from .core import SecureModelMixin, UserSelectSerializer


# ===== DOCUMENT TYPE SERIALIZERS =====

class DocumentTypeSerializer(SecureModelMixin, serializers.ModelSerializer):
    """Serializer for document types with DMS compliance settings"""
    approval_template_name = serializers.CharField(
        source='approval_template.template_name', read_only=True, allow_null=True
    )

    class Meta:
        model = DocumentType
        fields = ('id', 'name', 'code', 'description', 'requires_approval',
                  'approval_template', 'approval_template_name',
                  'default_review_period_days', 'default_retention_days',
                  'created_at', 'updated_at', 'archived')
        read_only_fields = ('created_at', 'updated_at')


# ===== DOCUMENT SERIALIZERS =====

class DocumentsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced documents serializer using model methods"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_info = serializers.SerializerMethodField()
    content_type_info = serializers.SerializerMethodField()
    access_info = serializers.SerializerMethodField()
    auto_properties = serializers.SerializerMethodField()
    approved_by_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_type_info = serializers.SerializerMethodField()
    # Accept document_type_code as alternative to document_type ID
    document_type_code = serializers.CharField(write_only=True, required=False)
    # DMS Compliance computed fields
    is_due_for_review = serializers.BooleanField(read_only=True)
    days_until_review = serializers.IntegerField(read_only=True, allow_null=True)
    is_past_retention = serializers.BooleanField(read_only=True)

    class Meta:
        model = Documents
        fields = ('id', 'classification', 'ai_readable', 'is_image', 'file_name', 'file', 'file_url', 'upload_date',
                  'uploaded_by', 'uploaded_by_info', 'content_type', 'object_id', 'content_type_info', 'version',
                  'access_info', 'auto_properties',
                  'status', 'status_display', 'approved_by', 'approved_by_info', 'approved_at',
                  'document_type', 'document_type_code', 'document_type_info', 'change_justification',
                  'previous_version', 'is_current_version',
                  # DMS Compliance fields
                  'effective_date', 'review_date', 'obsolete_date', 'retention_until',
                  'is_due_for_review', 'days_until_review', 'is_past_retention',
                  # ITAR / Export Control fields
                  'itar_controlled', 'eccn', 'export_control_reason',
                  'created_at', 'updated_at')
        read_only_fields = (
            'upload_date', 'created_at', 'updated_at', 'archived', 'file_url', 'uploaded_by_info', 'content_type_info',
            'access_info', 'auto_properties', 'approved_by', 'approved_at', 'status_display', 'document_type_info',
            'previous_version', 'is_current_version',
            # DMS Compliance - these are calculated on release, not editable
            'effective_date', 'review_date', 'obsolete_date', 'retention_until',
            'is_due_for_review', 'days_until_review', 'is_past_retention')

    @extend_schema_field(serializers.CharField())
    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_uploaded_by_info(self, obj):
        if obj.uploaded_by:
            return UserSelectSerializer(obj.uploaded_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_content_type_info(self, obj):
        if obj.content_type:
            return {'app_label': obj.content_type.app_label, 'model': obj.content_type.model,
                    'name': str(obj.content_type)}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_access_info(self, obj):
        """Use model methods for access control"""
        request = self.context.get('request')
        if request and request.user:
            return {'can_access': obj.user_can_access(request.user),
                    'access_level': obj.get_access_level_for_user(request.user)}
        return {'can_access': False, 'access_level': 'no_access'}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_auto_properties(self, obj):
        """Use model method for auto-detected properties"""
        return obj.auto_detect_properties()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_approved_by_info(self, obj):
        if obj.approved_by:
            return UserSelectSerializer(obj.approved_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_document_type_info(self, obj):
        if obj.document_type:
            return DocumentTypeSerializer(obj.document_type).data
        return None

    def create(self, validated_data):
        """Enhanced create using model methods"""
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user

        # Handle document_type_code -> document_type lookup
        document_type_code = validated_data.pop('document_type_code', None)
        if document_type_code and not validated_data.get('document_type'):
            try:
                doc_type = DocumentType.objects.get(code=document_type_code)
                validated_data['document_type'] = doc_type
            except DocumentType.DoesNotExist:
                pass  # Silently ignore invalid codes

        document = Documents(**validated_data)
        auto_properties = document.auto_detect_properties(validated_data.get('file'))

        for key, value in auto_properties.items():
            if key not in validated_data or not validated_data[key]:
                validated_data[key] = value

        return super().create(validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    """Alternative document serializer for compatibility"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    content_type_model = serializers.SerializerMethodField()
    access_level = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = ["id", "is_image", "file_name", "file", "file_url", "upload_date", "uploaded_by", "uploaded_by_name",
                  "content_type", "content_type_model", "object_id", "version", "classification", "access_level",
                  "ai_readable"]
        read_only_fields = ["upload_date", "uploaded_by_name", "file_url", "content_type_model", "access_level"]

    def get_file_url(self, obj) -> str | None:
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None

    def get_uploaded_by_name(self, obj) -> str:
        if obj.uploaded_by:
            first = obj.uploaded_by.first_name or ""
            last = obj.uploaded_by.last_name or ""
            return f"{first} {last}".strip() or obj.uploaded_by.username
        return "Unknown"

    def get_content_type_model(self, obj) -> str | None:
        return obj.content_type.model if obj.content_type else None

    def get_access_level(self, obj) -> str:
        """Use model method for access level"""
        request = self.context.get('request')
        if request and request.user:
            return obj.get_access_level_for_user(request.user)
        return "no_access"

    def validate_file(self, file):
        if not file.name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".docx")):
            raise serializers.ValidationError("Unsupported file type.")
        return file

    def create(self, validated_data):
        request = self.context.get("request")
        file = validated_data.get("file")

        document = Documents(**validated_data)
        auto_properties = document.auto_detect_properties(file)

        for key, value in auto_properties.items():
            if key not in validated_data:
                validated_data[key] = value

        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user

        return super().create(validated_data)


# ===== 3D MODEL SERIALIZERS =====

class ThreeDModelSerializer(SecureModelMixin, serializers.ModelSerializer):
    """
    Serializer for 3D model files.

    Includes processing status for async conversion workflow:
    - pending: Uploaded, waiting for processing
    - processing: Currently being converted/optimized
    - completed: Ready for viewing
    - failed: Processing error (see processing_error field)
    """
    part_type_display = serializers.CharField(source='part_type.__str__', read_only=True)
    step_display = serializers.CharField(source='step.__str__', read_only=True)
    annotation_count = serializers.SerializerMethodField()
    part_type = serializers.PrimaryKeyRelatedField(
        queryset=PartTypes.objects.all(),
        required=True,
        allow_null=False
    )
    step = serializers.PrimaryKeyRelatedField(
        queryset=Steps.objects.all(),
        required=False,
        allow_null=True
    )

    # Processing status fields
    is_ready = serializers.SerializerMethodField()
    processing_metrics = serializers.SerializerMethodField()

    def to_internal_value(self, data):
        """Handle FormData sending 'null' as string for optional ForeignKey fields"""
        if hasattr(data, '_mutable'):
            data._mutable = True
        else:
            data = data.copy() if hasattr(data, 'copy') else dict(data)

        for field in ['part_type', 'step']:
            if field in data:
                value = data[field]
                if isinstance(value, str) and value.lower() in ('null', 'undefined', ''):
                    data[field] = None

        return super().to_internal_value(data)

    class Meta:
        model = ThreeDModel
        fields = [
            'id', 'name', 'file', 'part_type', 'part_type_display', 'step', 'step_display',
            'uploaded_at', 'file_type', 'annotation_count',
            # Processing status
            'processing_status', 'processing_error', 'processed_at',
            'is_ready', 'processing_metrics',
            # Original file info
            'original_filename', 'original_format', 'original_size_bytes',
            # Timestamps
            'created_at', 'updated_at', 'archived', 'deleted_at'
        ]
        read_only_fields = [
            'uploaded_at', 'file_type', 'created_at', 'updated_at', 'deleted_at',
            'processing_status', 'processing_error', 'processed_at',
            'original_filename', 'original_format', 'original_size_bytes',
            'face_count', 'vertex_count', 'final_size_bytes',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_annotation_count(self, obj):
        """Get count of annotations on this model"""
        return obj.annotations.filter(archived=False).count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_ready(self, obj) -> bool:
        """True if model is processed and ready for viewing."""
        return obj.processing_status == 'completed'

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_processing_metrics(self, obj) -> dict | None:
        """Return processing metrics if model is completed."""
        if obj.processing_status != 'completed':
            return None

        return {
            'face_count': obj.face_count,
            'vertex_count': obj.vertex_count,
            'original_size': obj.original_size_bytes,
            'final_size': obj.final_size_bytes,
            'compression_ratio': obj.compression_ratio,
        }


# ===== HEATMAP ANNOTATION SERIALIZERS =====

class HeatMapAnnotationsSerializer(SecureModelMixin, serializers.ModelSerializer):
    """Serializer for heatmap annotations"""
    model_display = serializers.CharField(source='model.__str__', read_only=True)
    part_display = serializers.CharField(source='part.__str__', read_only=True)
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = HeatMapAnnotations
        fields = [
            'id', 'model', 'model_display', 'part', 'part_display',
            'position_x', 'position_y', 'position_z',
            'measurement_value', 'defect_type', 'severity',
            'notes', 'quality_reports', 'created_by', 'created_by_display', 'created_at', 'updated_at',
            'archived', 'deleted_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'deleted_at']

    @extend_schema_field(serializers.CharField())
    def get_created_by_display(self, obj):
        """Get full name of creator"""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    def create(self, validated_data):
        """Set created_by to current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


# ===== CHAT SESSION SERIALIZERS =====

class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for AI chat sessions"""

    class Meta:
        model = ChatSession
        fields = ['id', 'langgraph_thread_id', 'title', 'is_archived', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Set user to current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)
