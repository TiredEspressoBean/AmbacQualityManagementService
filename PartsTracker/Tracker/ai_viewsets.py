from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from pgvector.django import CosineDistance
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer

from .models import DocChunk, Documents
from .serializer import DocumentsSerializer


class EmbeddingViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    def dispatch(self, request, *args, **kwargs):
        """Debug auth token from LangGraph"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"EmbeddingViewSet - Auth header: {auth_header}")
        if hasattr(request, 'user'):
            print(f"EmbeddingViewSet - User: {request.user}, authenticated: {request.user.is_authenticated}")
        return super().dispatch(request, *args, **kwargs)
    
    @extend_schema(
        request=inline_serializer(
            name='EmbedQueryRequest',
            fields={
                'query': serializers.CharField(help_text='Text to embed for vector search')
            }
        ),
        responses=inline_serializer(
            name='EmbedQueryResponse', 
            fields={
                'embedding': serializers.ListField(child=serializers.FloatField())
            }
        )
    )
    @action(detail=False, methods=['post'])
    def embed_query(self, request):
        """Embed a single query for vector search"""
        query = request.data.get('query', '')
        if not query:
            return Response({"detail": "Query required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .ai_embed import embed_texts
            embeddings = embed_texts([query])
            return Response({'embedding': embeddings[0]})
        except Exception as e:
            return Response(
                {"detail": f"Embedding failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AISearchViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    def dispatch(self, request, *args, **kwargs):
        """Debug auth token from LangGraph"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"AISearchViewSet - Auth header: {auth_header}")
        if hasattr(request, 'user'):
            print(f"AISearchViewSet - User: {request.user}, authenticated: {request.user.is_authenticated}")
        return super().dispatch(request, *args, **kwargs)
    
    @extend_schema(
        request=inline_serializer(
            name='VectorSearchRequest',
            fields={
                'embedding': serializers.ListField(child=serializers.FloatField()),
                'limit': serializers.IntegerField(default=10),
                'threshold': serializers.FloatField(default=0.7),
                'doc_ids': serializers.ListField(child=serializers.IntegerField(), required=False)
            }
        ),
        responses=inline_serializer(name='VectorSearchResponse', fields={'results': serializers.ListField()})
    )
    @action(detail=False, methods=['post'])
    def vector_search(self, request):
        """Vector similarity search on document chunks"""
        query_embedding = request.data.get('embedding')
        limit = request.data.get('limit', 10)
        threshold = request.data.get('threshold', 0.7)
        doc_ids = request.data.get('doc_ids', [])
        
        if not query_embedding:
            return Response({"detail": "embedding required"}, status=status.HTTP_400_BAD_REQUEST)
        
        chunks = DocChunk.objects.all()
        
        # Filter by specific documents if provided
        if doc_ids:
            chunks = chunks.filter(doc_id__in=doc_ids)
        
        chunks = chunks.annotate(
            similarity=CosineDistance('embedding', query_embedding)
        ).filter(
            similarity__gte=threshold
        ).order_by('-similarity')[:limit]
        
        return Response({
            'query_params': {
                'limit': limit,
                'threshold': threshold,
                'doc_filter_count': len(doc_ids) if doc_ids else None
            },
            'results': [{
                'id': chunk.id,
                'similarity': float(chunk.similarity),
                'preview_text': chunk.preview_text,
                'full_text': chunk.full_text,
                'span_meta': chunk.span_meta,
                'doc_id': chunk.doc_id,
                'doc_name': chunk.doc.file_name
            } for chunk in chunks]
        })
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search query text'
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Max results to return (default: 20)'
            ),
            OpenApiParameter(
                name='doc_ids',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter to specific document IDs (can be provided multiple times)',
                many=True
            )
        ],
        responses=inline_serializer(
            name='KeywordSearchResponse',
            fields={
                'query': serializers.CharField(),
                'total_results': serializers.IntegerField(),
                'results': serializers.ListField(child=serializers.DictField())
            }
        )
    )
    @action(detail=False, methods=['get'])
    def keyword_search(self, request):
        """Full-text search on document chunks"""
        query = request.query_params.get('q', '')
        limit = int(request.query_params.get('limit', 20))
        doc_ids = request.query_params.getlist('doc_ids', [])
        
        if not query:
            return Response({"detail": "query parameter 'q' required"}, status=status.HTTP_400_BAD_REQUEST)
        
        chunks = DocChunk.objects.select_related('doc').all()
        
        # Filter by specific documents if provided
        if doc_ids:
            chunks = chunks.filter(doc_id__in=doc_ids)
        
        # PostgreSQL full-text search
        search_query = SearchQuery(query)
        chunks = chunks.annotate(
            search_vector=SearchVector('preview_text', 'full_text'),
            rank=SearchRank(SearchVector('preview_text', 'full_text'), search_query)
        ).filter(
            search_vector=search_query
        ).order_by('-rank')[:limit]
        
        return Response({
            'query': query,
            'query_params': {
                'limit': limit,
                'doc_filter_count': len(doc_ids) if doc_ids else None
            },
            'results': [{
                'id': chunk.id,
                'rank': float(chunk.rank),
                'preview_text': chunk.preview_text,
                'full_text': chunk.full_text,
                'span_meta': chunk.span_meta,
                'doc_id': chunk.doc_id,
                'doc_name': chunk.doc.file_name
            } for chunk in chunks]
        })
    
    @extend_schema(
        request=inline_serializer(
            name='HybridSearchRequest',
            fields={
                'query': serializers.CharField(required=False, help_text='Text query for keyword search'),
                'embedding': serializers.ListField(
                    child=serializers.FloatField(),
                    required=False,
                    help_text='Pre-computed embedding vector for similarity search'
                ),
                'limit': serializers.IntegerField(required=False, help_text='Max results to return'),
                'vector_threshold': serializers.FloatField(required=False, help_text='Minimum similarity threshold'),
                'doc_ids': serializers.ListField(
                    child=serializers.IntegerField(),
                    required=False,
                    help_text='Filter to specific document IDs'
                )
            }
        ),
        responses=inline_serializer(
            name='HybridSearchResponse',
            fields={
                'query': serializers.CharField(),
                'has_embedding': serializers.BooleanField(),
                'total_results': serializers.IntegerField(),
                'results': serializers.ListField(child=serializers.DictField())
            }
        )
    )
    @action(detail=False, methods=['post'])
    def hybrid_search(self, request):
        """Combine vector similarity and keyword search results"""
        query = request.data.get('query', '')
        query_embedding = request.data.get('embedding')
        limit = request.data.get('limit', 10)
        vector_threshold = request.data.get('vector_threshold', 0.7)
        doc_ids = request.data.get('doc_ids', [])
        
        if not query and not query_embedding:
            return Response({"detail": "Either 'query' or 'embedding' required"}, status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        
        # Vector search if embedding provided
        if query_embedding:
            vector_chunks = DocChunk.objects.all()
            if doc_ids:
                vector_chunks = vector_chunks.filter(doc_id__in=doc_ids)
            
            vector_chunks = vector_chunks.annotate(
                similarity=CosineDistance('embedding', query_embedding)
            ).filter(
                similarity__gte=vector_threshold
            ).order_by('-similarity')[:limit]
            
            for chunk in vector_chunks:
                results.append({
                    'id': chunk.id,
                    'score': float(chunk.similarity),
                    'score_type': 'vector_similarity',
                    'preview_text': chunk.preview_text,
                    'full_text': chunk.full_text,
                    'span_meta': chunk.span_meta,
                    'doc_id': chunk.doc_id,
                    'doc_name': chunk.doc.file_name
                })
        
        # Keyword search if query provided
        if query:
            keyword_chunks = DocChunk.objects.select_related('doc').all()
            if doc_ids:
                keyword_chunks = keyword_chunks.filter(doc_id__in=doc_ids)
            
            search_query = SearchQuery(query)
            keyword_chunks = keyword_chunks.annotate(
                search_vector=SearchVector('preview_text', 'full_text'),
                rank=SearchRank(SearchVector('preview_text', 'full_text'), search_query)
            ).filter(
                search_vector=search_query
            ).order_by('-rank')[:limit]
            
            # Add keyword results, avoiding duplicates
            existing_ids = {r['id'] for r in results}
            for chunk in keyword_chunks:
                if chunk.id not in existing_ids:
                    results.append({
                        'id': chunk.id,
                        'score': float(chunk.rank),
                        'score_type': 'keyword_rank',
                        'preview_text': chunk.preview_text,
                        'full_text': chunk.full_text,
                        'span_meta': chunk.span_meta,
                        'doc_id': chunk.doc_id,
                        'doc_name': chunk.doc.file_name
                    })
        
        return Response({
            'query': query,
            'has_embedding': bool(query_embedding),
            'total_results': len(results),
            'results': results
        })
    
    @extend_schema(
        request=inline_serializer(
            name='ContextWindowRequest',
            fields={
                'chunk_id': serializers.IntegerField(help_text='ID of the chunk to center the window on'),
                'window_size': serializers.IntegerField(required=False, help_text='Number of chunks before/after center (default: 2)')
            }
        ),
        responses=inline_serializer(
            name='ContextWindowResponse',
            fields={
                'center_chunk_id': serializers.IntegerField(),
                'center_index': serializers.IntegerField(),
                'window_size': serializers.IntegerField(),
                'doc_name': serializers.CharField(),
                'chunks': serializers.ListField(child=serializers.DictField())
            }
        )
    )
    @action(detail=False, methods=['post'])
    def get_context_window(self, request):
        """Get chunk plus surrounding chunks using span_meta ordering"""
        chunk_id = request.data.get('chunk_id')
        window_size = request.data.get('window_size', 2)  # chunks before/after
        
        if not chunk_id:
            return Response({"detail": "chunk_id required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            center_chunk = DocChunk.objects.select_related('doc').get(
                id=chunk_id
            )
        except DocChunk.DoesNotExist:
            return Response({"detail": "Chunk not found or not accessible"}, status=status.HTTP_404_NOT_FOUND)
        
        center_index = center_chunk.span_meta.get('i', 0)
        doc_id = center_chunk.doc_id
        
        # Get chunks in window range
        min_index = max(0, center_index - window_size)
        max_index = center_index + window_size
        
        window_chunks = DocChunk.objects.filter(
            doc_id=doc_id,
            span_meta__i__gte=min_index,
            span_meta__i__lte=max_index
        ).order_by('span_meta__i')
        
        return Response({
            'center_chunk_id': chunk_id,
            'center_index': center_index,
            'window_size': window_size,
            'doc_name': center_chunk.doc.file_name,
            'chunks': [{
                'id': chunk.id,
                'index': chunk.span_meta.get('i', 0),
                'is_center': chunk.id == chunk_id,
                'preview_text': chunk.preview_text,
                'full_text': chunk.full_text,
                'span_meta': chunk.span_meta
            } for chunk in window_chunks]
        })


class QueryViewSet(viewsets.ViewSet):
    """READ-ONLY query interface for safe ORM operations via LLM"""
    permission_classes = [AllowAny]
    
    def dispatch(self, request, *args, **kwargs):
        """Debug auth token from LangGraph"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"QueryViewSet - Auth header: {auth_header}")
        if hasattr(request, 'user'):
            print(f"QueryViewSet - User: {request.user}, authenticated: {request.user.is_authenticated}")
        return super().dispatch(request, *args, **kwargs)
    
    # Whitelist of allowed models for read operations
    ALLOWED_MODELS = {
        'Orders': [
            'id', 'name', 'order_status', 'customer', 'company', 'created_at', 'updated_at', 
            'estimated_completion', 'version', 'archived'
        ],
        'Parts': [
            'id', 'ERP_id', 'part_status', 'created_at', 'updated_at', 'order', 'work_order', 
            'step', 'part_type', 'requires_sampling', 'version', 'archived'
        ],
        'WorkOrder': [
            'id', 'ERP_id', 'expected_completion', 'true_completion', 'notes', 'related_order',
            'quantity', 'created_at', 'updated_at', 'version', 'archived', 'workorder_status'
        ],
        'User': [
            'id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active',
            'date_joined', 'parent_company'
        ],
        'Companies': [
            'id', 'name', 'created_at', 'updated_at', 'hubspot_id', 'version', 'archived'
        ],
        'Steps': [
            'id', 'name', 'process', 'expected_duration_hours', 'description', 'order',
            'is_final', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'Processes': [
            'id', 'name', 'part_type', 'remanufacturing', 'is_batch_process', 'created_at', 
            'updated_at', 'version', 'archived'
        ],
        'PartTypes': [
            'id', 'name', 'ID_prefix', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'Documents': [
            'id', 'file_name', 'upload_date', 'content_type', 'object_id', 'is_image',
            'uploaded_by', 'version', 'ai_readable', 'created_at', 'updated_at', 'archived'
        ],
        'QualityReports': [
            'id', 'part', 'equipment', 'operator', 'description', 'created_at', 'updated_at',
            'version', 'archived'
        ],
        'QualityErrorsList': [
            'id', 'error_name', 'part_type', 'example', 'created_at', 'updated_at', 
            'version', 'archived'
        ],
        'Equipments': [
            'id', 'name', 'equipment_type', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'EquipmentType': [
            'id', 'name', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'MeasurementDefinition': [
            'id', 'step', 'label', 'type', 'unit', 'nominal', 'tolerance_positive', 
            'tolerance_negative', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'MeasurementResult': [
            'id', 'report', 'definition', 'value_numeric', 'value_pass_fail', 'created_at',
            'updated_at', 'version', 'archived'
        ],
        'SamplingRuleSet': [
            'id', 'part_type', 'process', 'step', 'name', 'active', 'version', 'origin',
            'fallback_threshold', 'fallback_duration_hours', 'created_at', 'updated_at', 'archived'
        ],
        'SamplingRule': [
            'id', 'ruleset', 'rule_type', 'order', 'n_value', 'percentage_value', 'created_at',
            'updated_at', 'version', 'archived'
        ],
        'StepTransitionLog': [
            'id', 'part', 'to_step', 'operator', 'timestamp', 'created_at', 'updated_at',
            'version', 'archived'
        ],
        'EquipmentUsage': [
            'id', 'part', 'step', 'equipment', 'operator', 'start_time', 'end_time',
            'error_report', 'created_at', 'updated_at', 'version', 'archived'
        ],
        'ExternalAPIOrderIdentifier': [
            'id', 'order', 'external_id', 'source_name', 'created_at', 'updated_at',
            'version', 'archived'
        ],
        'QaApproval': [
            'id', 'step', 'work_order', 'qa_staff', 'approved_at', 'created_at', 'updated_at',
            'version', 'archived'
        ],
        'DocChunk': [
            'id', 'doc', 'preview_text', 'full_text', 'span_meta'
        ]
    }
    
    # Only allow these safe query operations
    ALLOWED_OPERATIONS = [
        'exact', 'iexact', 'contains', 'icontains', 'startswith', 'istartswith', 
        'endswith', 'iendswith', 'gt', 'gte', 'lt', 'lte', 'in', 'range',
        'date', 'year', 'month', 'day', 'week_day', 'isnull'
    ]
    
    # Allow relationship traversal for these fields (one level deep)
    ALLOWED_RELATIONSHIPS = {
        'Orders': {
            'customer__username', 'customer__first_name', 'customer__last_name', 'customer__email',
            'company__name', 'company__hubspot_id'
        },
        'Parts': {
            'order__name', 'order__order_status', 'work_order__ERP_id', 'step__name', 
            'part_type__name', 'part_type__ID_prefix'
        },
        'WorkOrder': {
            'related_order__name', 'related_order__order_status', 'related_order__customer__username'
        },
        'QualityReports': {
            'part__ERP_id', 'part__part_status', 'equipment__name', 'operator__username'
        },
        'Steps': {
            'process__name', 'process__part_type__name'
        },
        'Processes': {
            'part_type__name', 'part_type__ID_prefix'
        },
        'Documents': {
            'uploaded_by__username', 'uploaded_by__first_name', 'uploaded_by__last_name'
        },
        'MeasurementResult': {
            'report__part__ERP_id', 'definition__label', 'definition__step__name'
        },
        'EquipmentUsage': {
            'part__ERP_id', 'step__name', 'equipment__name', 'operator__username'
        },
        'SamplingRuleSet': {
            'part_type__name', 'process__name', 'step__name'
        },
        'StepTransitionLog': {
            'part__ERP_id', 'to_step__name', 'operator__username'
        }
    }
    
    @extend_schema(
        responses=inline_serializer(
            name='QuerySchemaResponse',
            fields={
                'allowed_models': serializers.DictField(help_text='Available models and their queryable fields'),
                'allowed_operations': serializers.ListField(
                    child=serializers.CharField(), 
                    help_text='Allowed filter operations (exact, contains, etc.)'
                ),
                'examples': serializers.DictField(help_text='Example query structures')
            }
        )
    )
    def _get_model_fields(self, model_class):
        """Get actual field names from Django model introspection"""
        from django.db import models
        
        fields = []
        for field in model_class._meta.get_fields():
            # Skip reverse foreign keys and many-to-many reverse relations
            if hasattr(field, 'related_model') and field.related_model and hasattr(field, 'related_name'):
                continue
                
            # Include regular fields and forward foreign keys
            if isinstance(field, (models.Field, models.ForeignKey, models.OneToOneField)):
                fields.append(field.name)
                
        return sorted(fields)
    
    def _get_actual_model_schema(self):
        """Get actual model schemas using Django introspection"""
        from django.apps import apps
        actual_schemas = {}
        
        for model_name in self.ALLOWED_MODELS.keys():
            try:
                model_class = apps.get_model('Tracker', model_name)
                actual_schemas[model_name] = self._get_model_fields(model_class)
            except Exception as e:
                actual_schemas[model_name] = f"Error: {str(e)}"
                
        return actual_schemas

    @action(detail=False, methods=['get'])
    def schema_info(self, request):
        """Return model schema information for safe ORM query building"""
        # Get both hardcoded and actual schemas for comparison
        actual_schemas = self._get_actual_model_schema()
        
        return Response({
            "allowed_models": self.ALLOWED_MODELS,
            "actual_model_fields": actual_schemas,
            "allowed_operations": self.ALLOWED_OPERATIONS,
            "examples": {
                "filter_orders_by_status": {
                    "model": "Orders",
                    "filters": {"order_status": "PENDING"}
                },
                "search_parts_by_erp": {
                    "model": "Parts", 
                    "filters": {"ERP_id__icontains": "ABC123"}
                },
                "count_completed_parts": {
                    "model": "Parts",
                    "filters": {"part_status": "COMPLETED"},
                    "aggregate": "count"
                }
            }
        })
    
    @extend_schema(
        request=inline_serializer(
            name='ExecuteQueryRequest',
            fields={
                'model': serializers.CharField(help_text='Model name to query'),
                'filters': serializers.DictField(required=False, help_text='Filters to apply'),
                'fields': serializers.ListField(
                    child=serializers.CharField(), 
                    required=False, 
                    help_text='Specific fields to return'
                ),
                'limit': serializers.IntegerField(required=False, help_text='Max results (up to 100)'),
                'aggregate': serializers.CharField(required=False, help_text='Aggregation function (count)')
            }
        ),
        responses=inline_serializer(
            name='ExecuteQueryResponse',
            fields={
                'model': serializers.CharField(),
                'filters': serializers.DictField(),
                'count': serializers.IntegerField(),
                'limit': serializers.IntegerField(),
                'results': serializers.ListField(child=serializers.DictField())
            }
        )
    )
    @action(detail=False, methods=['post'])
    def execute_read_only(self, request):
        """Execute SAFE READ-ONLY ORM queries with strict validation"""
        model_name = request.data.get('model')
        filters = request.data.get('filters', {})
        fields = request.data.get('fields', [])
        limit = min(request.data.get('limit', 50), 100)  # Max 100 results
        aggregate = request.data.get('aggregate')  # count, max, min, avg
        
        # Validate model is allowed
        if model_name not in self.ALLOWED_MODELS:
            return Response({
                "error": f"Model '{model_name}' not allowed",
                "allowed_models": list(self.ALLOWED_MODELS.keys())
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get actual model fields using introspection
        from django.apps import apps
        model_class = apps.get_model('Tracker', model_name)
        allowed_fields = self._get_model_fields(model_class)
        allowed_relationships = self.ALLOWED_RELATIONSHIPS.get(model_name, set())
        
        if fields:
            invalid_fields = []
            for field in fields:
                if field not in allowed_fields and field not in allowed_relationships:
                    invalid_fields.append(field)
            
            if invalid_fields:
                return Response({
                    "error": f"Fields {invalid_fields} not allowed for {model_name}",
                    "allowed_fields": allowed_fields,
                    "allowed_relationships": list(allowed_relationships)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate filters contain only safe operations
        for filter_key, filter_value in filters.items():
            # Parse filter key (e.g., "customer__name__icontains" -> base="customer__name", op="icontains")
            parts = filter_key.split('__')
            if len(parts) == 1:
                base_field = parts[0]
                operation = 'exact'
            else:
                # Check if last part is an operation
                if parts[-1] in self.ALLOWED_OPERATIONS:
                    operation = parts[-1]
                    base_field = '__'.join(parts[:-1])
                else:
                    operation = 'exact'
                    base_field = filter_key
            
            # Validate field is allowed (direct field or relationship)
            field_allowed = (
                base_field in allowed_fields or 
                base_field in allowed_relationships
            )
            
            if not field_allowed:
                return Response({
                    "error": f"Field '{base_field}' not allowed for {model_name}",
                    "allowed_fields": allowed_fields,
                    "allowed_relationships": list(allowed_relationships)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if operation not in self.ALLOWED_OPERATIONS:
                return Response({
                    "error": f"Operation '{operation}' not allowed",
                    "allowed_operations": self.ALLOWED_OPERATIONS
                }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Import model dynamically
            from django.apps import apps
            model_class = apps.get_model('Tracker', model_name)
            
            # Skip user filtering for now - use all records
            queryset = model_class.objects.all()
            
            # Apply filters
            if filters:
                queryset = queryset.filter(**filters)
            
            # Handle aggregation
            if aggregate:
                if aggregate == 'count':
                    result = queryset.count()
                    return Response({"result": result, "aggregate": aggregate})
                else:
                    return Response({
                        "error": f"Aggregate '{aggregate}' not implemented"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Apply field selection and limit
            if fields:
                queryset = queryset.values(*fields)
            else:
                # Convert foreign key fields to _id fields for serialization
                from django.db import models
                safe_fields = []
                for field_name in allowed_fields:
                    try:
                        field = model_class._meta.get_field(field_name)
                        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                            safe_fields.append(f"{field_name}_id")
                        else:
                            safe_fields.append(field_name)
                    except:
                        # If field lookup fails, include as-is
                        safe_fields.append(field_name)
                queryset = queryset.values(*safe_fields)

            results = list(queryset[:limit])
            
            return Response({
                "model": model_name,
                "filters": filters,
                "count": len(results),
                "limit": limit,
                "results": results
            })
            
        except Exception as e:
            return Response({
                "error": f"Query execution failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)