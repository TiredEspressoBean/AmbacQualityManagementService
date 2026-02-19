"""
Graph traversal utilities for model hierarchies.

Provides utilities to traverse SecureModel hierarchies and query
attachable models (Documents, Annotations, Approvals, etc.) within
that graph.

Core Functions:
    get_descendants(obj)    - Get all objects below this node
    get_ancestors(obj)      - Get all objects above this node
    related_to(Model, obj)  - Query attachables (Documents, etc.) for a subtree

Filtering:
    max_depth               - Limit traversal depth
    include_types           - Only traverse these model types
    exclude_types           - Skip these model types

Utilities:
    find_in_graph()         - Find first object matching a condition
    count_descendants()     - Count objects by type
    merge_scopes()          - Combine multiple traversal results (union)
    subtract_scope()        - Remove one scope from another (difference)
    explain_path()          - Find and describe path between two objects

Usage Examples:
    from Tracker.scope import get_descendants, get_ancestors, related_to

    # Get all objects below an order in the hierarchy
    objects_by_type = get_descendants(order)
    # Returns: {content_type_id: {obj_id, obj_id, ...}, ...}

    # Get all documents related to an order and its descendants
    docs = related_to(Documents, order, user)

    # Limit depth of traversal
    objects_by_type = get_descendants(order, max_depth=2)

    # Filter to specific model types
    from Tracker.models import Parts, QualityReports
    objects_by_type = get_descendants(order, include_types=[Parts, QualityReports])

    # Exclude certain types
    objects_by_type = get_descendants(order, exclude_types=[AuditLog])

    # Find first matching object
    part = find_in_graph(order, lambda obj: obj._meta.model_name == 'parts')

    # Count descendants by type
    counts = count_descendants(order)
    # Returns: {'parts': 5, 'workorder': 2, 'qualityreports': 3}

    # Combine scopes from multiple orders
    scope1 = get_descendants(order1)
    scope2 = get_descendants(order2)
    combined = merge_scopes(scope1, scope2)

    # Find path between objects
    path = explain_path(order, step)
    # Returns: [(order, 'parts'), (part, 'part_type'), (process, 'steps'), (step, None)]
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related import ForeignObjectRel


# Cache for ContentType lookups
_content_type_cache = {}


def _get_content_type(model_or_obj):
    """Get ContentType for a model or instance, with caching."""
    if hasattr(model_or_obj, '_meta'):
        key = model_or_obj._meta.label
    else:
        key = model_or_obj

    if key not in _content_type_cache:
        _content_type_cache[key] = ContentType.objects.get_for_model(model_or_obj)

    return _content_type_cache[key]


def _traverse(obj, direction='down', max_depth=None, include_types=None,
              exclude_types=None, stop_condition=None, preserve_structure=False,
              user=None):
    """
    Core graph traversal logic with batched queries.

    Args:
        obj: The starting object
        direction: 'down' follows reverse FKs (to children),
                   'up' follows forward FKs (to parents)
        max_depth: Maximum depth to traverse (None for unlimited)
        include_types: List of model classes to include (None for all SecureModels)
        exclude_types: List of model classes to exclude
        stop_condition: Callable(obj) that returns True to stop and return that object
        preserve_structure: If True, return nested dict structure instead of flat
        user: Optional user for permission filtering via for_user()

    Returns:
        If stop_condition triggers: the matching object
        If preserve_structure: nested dict {obj: {child_obj: {...}, ...}}
        Otherwise: dict of {content_type_id: set(object_ids)}
    """
    from .models.core import SecureModel

    # Convert type filters to sets of model names for fast lookup
    allowed_types = None
    if include_types:
        allowed_types = {m._meta.model_name for m in include_types}

    excluded_types = None
    if exclude_types:
        excluded_types = {m._meta.model_name for m in exclude_types}

    visited = {}  # {content_type_id: set(object_ids)}
    structure = {} if preserve_structure else None
    obj_cache = {}  # {(content_type_id, pk): object} - for structure building

    # For batching: track what we need to fetch next
    # {model_class: {(parent_ct_id, parent_pk, field_name): set(ids_to_fetch)}}
    current_depth_objects = [obj]
    depth = 0

    while current_depth_objects:
        # Check depth limit
        if max_depth is not None and depth > max_depth:
            break

        # Process all objects at current depth, collect what to fetch next
        # {model_class: {'ids': set(), 'parents': [(parent_obj, field_name, child_id), ...]}}
        to_fetch = {}

        for current in current_depth_objects:
            if current is None:
                continue

            # Check stop condition
            if stop_condition and stop_condition(current):
                return current

            ct = _get_content_type(current)

            # Check if already visited
            if ct.id not in visited:
                visited[ct.id] = set()
            if current.pk in visited[ct.id]:
                continue
            visited[ct.id].add(current.pk)

            # Cache object for structure building
            obj_cache[(ct.id, current.pk)] = current

            # Track structure if requested
            if preserve_structure:
                current_node = {}
                # Find parent in structure or set as root
                parent_key = getattr(current, '_traverse_parent_key', None)
                if parent_key is None:
                    structure[current] = current_node
                else:
                    parent_obj = obj_cache.get(parent_key)
                    if parent_obj and parent_obj in structure:
                        structure[parent_obj][current] = current_node
                    elif parent_obj:
                        # Find parent's node in nested structure
                        _add_to_structure(structure, parent_obj, current, current_node)
                # Store node reference for children
                current._traverse_node = current_node

            # Discover related objects to fetch
            for field in current._meta.get_fields():
                if not field.is_relation:
                    continue
                if not field.related_model:
                    continue
                if not issubclass(field.related_model, SecureModel):
                    continue

                related_model_name = field.related_model._meta.model_name

                # Type filtering - include
                if allowed_types and related_model_name not in allowed_types:
                    continue

                # Type filtering - exclude
                if excluded_types and related_model_name in excluded_types:
                    continue

                is_reverse = isinstance(field, ForeignObjectRel)

                if direction == 'down':
                    if not is_reverse:
                        continue
                    # Reverse relation - need to query by the FK field
                    related_model = field.related_model
                    # Get the field name on the related model that points to us
                    remote_field_name = field.field.name
                    filter_field = f'{remote_field_name}__in'

                    # Key by (parent_model, related_model, filter_field) to prevent mixing parent IDs.
                    # IMPORTANT: Previously keyed by just (related_model, filter_field), which caused
                    # a bug where Part IDs were used as WorkOrder IDs when both Orders->Parts and
                    # WorkOrder->Parts relations existed. Including parent_model in the key makes
                    # it structurally impossible to mix parent IDs from different source models.
                    parent_model = current._meta.model
                    fetch_key = (parent_model, related_model, filter_field)
                    if fetch_key not in to_fetch:
                        to_fetch[fetch_key] = {
                            'model': related_model,
                            'filter_field': filter_field,
                            'parent_ids': set(),
                            'parents_map': {}  # {child_fk_value: [(parent_obj, field_accessor)]}
                        }

                    to_fetch[fetch_key]['parent_ids'].add(current.pk)
                    field_accessor = field.get_accessor_name()
                    if current.pk not in to_fetch[fetch_key]['parents_map']:
                        to_fetch[fetch_key]['parents_map'][current.pk] = []
                    to_fetch[fetch_key]['parents_map'][current.pk].append((current, field_accessor))

                else:  # direction == 'up'
                    if is_reverse:
                        continue
                    if field.many_to_many:
                        continue

                    # Forward FK - get the ID directly without fetching
                    fk_id = getattr(current, f'{field.name}_id', None)
                    if fk_id is None:
                        continue

                    related_model = field.related_model
                    filter_field = 'pk__in'

                    # Key by (parent_model, related_model, filter_field) for consistency with 'down' direction
                    parent_model = current._meta.model
                    fetch_key = (parent_model, related_model, filter_field)
                    if fetch_key not in to_fetch:
                        to_fetch[fetch_key] = {
                            'model': related_model,
                            'filter_field': filter_field,
                            'parent_ids': set(),
                            'parents_map': {}
                        }

                    to_fetch[fetch_key]['parent_ids'].add(fk_id)
                    if fk_id not in to_fetch[fetch_key]['parents_map']:
                        to_fetch[fetch_key]['parents_map'][fk_id] = []
                    to_fetch[fetch_key]['parents_map'][fk_id].append((current, field.name))

        # Batch fetch all related objects for next depth
        next_depth_objects = []

        # DEBUG: Uncomment to trace traversal
        # print(f'  Depth {depth}: fetching {[(m._meta.model_name, ff) for (m, ff) in to_fetch.keys()]}')

        for fetch_key, fetch_info in to_fetch.items():
            model_class = fetch_info['model']
            filter_field = fetch_info['filter_field']
            parent_ids = fetch_info['parent_ids']
            parents_map = fetch_info['parents_map']

            if not parent_ids:
                continue

            # Single query for all objects of this type
            # Use for_user() if available for permission filtering
            if user and hasattr(model_class.objects, 'for_user'):
                queryset = model_class.objects.for_user(user)
            else:
                queryset = model_class.objects.all()
            related_objects = list(queryset.filter(**{filter_field: parent_ids}))

            # DEBUG: Uncomment to trace large fetches
            # print(f'    {model_class._meta.model_name}: {len(related_objects)} objects via {filter_field} from {len(parent_ids)} parents')
            # if len(related_objects) > 100:
            #     print(f'      parent_ids: {list(parent_ids)[:10]}...')

            for rel_obj in related_objects:
                rel_ct = _get_content_type(rel_obj)

                # Skip if already visited
                if rel_ct.id in visited and rel_obj.pk in visited[rel_ct.id]:
                    continue

                # For structure: tag with parent info
                if preserve_structure:
                    if direction == 'down':
                        # Find parent by looking up which parent this object belongs to
                        fk_field = filter_field.replace('__in', '')
                        parent_id = getattr(rel_obj, f'{fk_field}_id', None)
                        if parent_id and parent_id in parents_map:
                            parent_obj = parents_map[parent_id][0][0]
                            parent_ct = _get_content_type(parent_obj)
                            rel_obj._traverse_parent_key = (parent_ct.id, parent_obj.pk)
                    else:
                        # Going up - the current objects are children of rel_obj
                        if rel_obj.pk in parents_map:
                            child_obj = parents_map[rel_obj.pk][0][0]
                            child_ct = _get_content_type(child_obj)
                            rel_obj._traverse_parent_key = (child_ct.id, child_obj.pk)

                next_depth_objects.append(rel_obj)

        current_depth_objects = next_depth_objects
        depth += 1

    if preserve_structure:
        return structure

    return visited


def _add_to_structure(structure, parent_obj, child_obj, child_node):
    """Helper to add child to nested structure by finding parent's node."""
    for root, root_node in structure.items():
        result = _find_and_add(root_node, parent_obj, child_obj, child_node)
        if result:
            return True
    return False


def _find_and_add(node, parent_obj, child_obj, child_node):
    """Recursively find parent and add child."""
    if parent_obj in node:
        node[parent_obj][child_obj] = child_node
        return True
    for child, child_dict in node.items():
        if _find_and_add(child_dict, parent_obj, child_obj, child_node):
            return True
    return False


def get_descendants(obj, max_depth=None, include_types=None, exclude_types=None,
                    preserve_structure=False, user=None):
    """
    Get all objects below this node in the hierarchy.

    Args:
        obj: The root object
        max_depth: Maximum depth to traverse (None for unlimited)
        include_types: List of model classes to include (None for all)
        exclude_types: List of model classes to exclude
        preserve_structure: If True, return nested dict instead of flat
        user: Optional user for permission filtering via for_user()

    Returns:
        dict of {content_type_id: set(object_ids)} including the root,
        or nested structure if preserve_structure=True
    """
    return _traverse(obj, direction='down', max_depth=max_depth,
                     include_types=include_types, exclude_types=exclude_types,
                     preserve_structure=preserve_structure, user=user)


def get_ancestors(obj, max_depth=None, include_types=None, exclude_types=None,
                  preserve_structure=False, user=None):
    """
    Get all objects above this node in the hierarchy.

    Args:
        obj: The starting object
        max_depth: Maximum depth to traverse (None for unlimited)
        include_types: List of model classes to include (None for all)
        exclude_types: List of model classes to exclude
        preserve_structure: If True, return nested dict instead of flat
        user: Optional user for permission filtering via for_user()

    Returns:
        dict of {content_type_id: set(object_ids)} including the object,
        or nested structure if preserve_structure=True
    """
    return _traverse(obj, direction='up', max_depth=max_depth,
                     include_types=include_types, exclude_types=exclude_types,
                     preserve_structure=preserve_structure, user=user)


def find_in_graph(obj, condition, direction='down', max_depth=None, exclude_types=None,
                  user=None):
    """
    Find first object in the graph matching a condition.

    Args:
        obj: The starting object
        condition: Callable(obj) that returns True for a match
        direction: 'down' for descendants, 'up' for ancestors
        max_depth: Maximum depth to search
        exclude_types: List of model classes to skip during traversal
        user: Optional user for permission filtering via for_user()

    Returns:
        The first matching object, or None if not found
    """
    result = _traverse(obj, direction=direction, max_depth=max_depth,
                       exclude_types=exclude_types, stop_condition=condition,
                       user=user)
    # If stop_condition matched, result is the object; otherwise it's the visited dict
    if isinstance(result, dict):
        return None
    return result


def count_descendants(obj, max_depth=None, include_types=None, exclude_types=None,
                      user=None):
    """
    Count objects below this node, grouped by type.

    Args:
        obj: The root object
        max_depth: Maximum depth to traverse
        include_types: List of model classes to include
        exclude_types: List of model classes to exclude
        user: Optional user for permission filtering via for_user()

    Returns:
        dict of {model_name: count} e.g. {'parts': 5, 'workorder': 2}
    """
    scope = get_descendants(obj, max_depth=max_depth, include_types=include_types,
                            exclude_types=exclude_types, user=user)
    counts = {}
    for ct_id, obj_ids in scope.items():
        ct = ContentType.objects.get_for_id(ct_id)
        counts[ct.model] = len(obj_ids)
    return counts


def merge_scopes(*scopes):
    """
    Merge multiple scope dicts into one (union).

    Args:
        *scopes: Multiple scope dicts from get_descendants/get_ancestors

    Returns:
        Combined scope dict with all objects from all inputs
    """
    merged = {}
    for scope in scopes:
        for ct_id, obj_ids in scope.items():
            if ct_id not in merged:
                merged[ct_id] = set()
            merged[ct_id].update(obj_ids)
    return merged


def subtract_scope(scope1, scope2):
    """
    Subtract scope2 from scope1 (set difference).

    Args:
        scope1: The base scope dict
        scope2: The scope to subtract

    Returns:
        New scope dict with objects in scope1 but not in scope2
    """
    result = {}
    for ct_id, obj_ids in scope1.items():
        if ct_id in scope2:
            diff = obj_ids - scope2[ct_id]
            if diff:
                result[ct_id] = diff
        else:
            result[ct_id] = obj_ids.copy()
    return result


def explain_path(from_obj, to_obj, direction='down', max_depth=10):
    """
    Find and explain the relationship path between two objects.

    Args:
        from_obj: Starting object
        to_obj: Target object to find
        direction: 'down' for descendants, 'up' for ancestors
        max_depth: Maximum depth to search

    Returns:
        List of (object, field_name) tuples representing the path,
        or None if no path found.

    Example:
        path = explain_path(order, step)
        # Returns: [(order, 'parts'), (part, 'part_type'), (part_type, 'processes'),
        #           (process, 'steps'), (step, None)]
    """
    from .models.core import SecureModel

    target_ct = _get_content_type(to_obj)
    target_pk = to_obj.pk

    # Track path to each visited node: {(ct_id, pk): [(obj, field_name), ...]}
    paths = {(_get_content_type(from_obj).id, from_obj.pk): [(from_obj, None)]}
    to_visit = [(from_obj, 0)]
    visited = set()

    while to_visit:
        current, depth = to_visit.pop(0)  # BFS for shortest path
        if depth > max_depth:
            continue

        ct = _get_content_type(current)
        key = (ct.id, current.pk)

        if key in visited:
            continue
        visited.add(key)

        # Check if we found the target
        if ct.id == target_ct.id and current.pk == target_pk:
            path = paths[key]
            # Clean up: remove None from last item, add target
            result = [(obj, field) for obj, field in path[:-1]]
            result.append((current, None))
            return result

        current_path = paths[key]

        for field in current._meta.get_fields():
            if not field.is_relation:
                continue
            if not field.related_model:
                continue
            if not issubclass(field.related_model, SecureModel):
                continue

            is_reverse = isinstance(field, ForeignObjectRel)

            if direction == 'down' and not is_reverse:
                continue
            if direction == 'up' and is_reverse:
                continue
            if direction == 'up' and field.many_to_many:
                continue

            try:
                if is_reverse:
                    field_name = field.get_accessor_name()
                    related = getattr(current, field_name, None)
                else:
                    field_name = field.name
                    related = getattr(current, field_name, None)

                if related is None:
                    continue

                # Get related objects
                if hasattr(related, 'all'):
                    related_objs = list(related.all())
                else:
                    related_objs = [related]

                for rel_obj in related_objs:
                    rel_ct = _get_content_type(rel_obj)
                    rel_key = (rel_ct.id, rel_obj.pk)
                    if rel_key not in paths:
                        # Record the path to this node
                        new_path = current_path[:-1] + [(current, field_name), (rel_obj, None)]
                        paths[rel_key] = new_path
                        to_visit.append((rel_obj, depth + 1))

            except AttributeError:
                continue

    return None  # No path found


def _build_generic_filter(objects_by_type):
    """
    Build a Q object to filter models with GenericForeignKey.

    Args:
        objects_by_type: dict of {content_type_id: set(object_ids)}

    Returns:
        Q object for filtering by content_type and object_id
    """
    from django.db.models import Q

    if not objects_by_type:
        return Q(pk__in=[])  # Match nothing

    q = Q()
    for content_type_id, object_ids in objects_by_type.items():
        if object_ids:
            q |= Q(content_type_id=content_type_id, object_id__in=object_ids)

    return q


def related_to(model_class, root_obj, user=None, direction='down',
               include_types=None, exclude_types=None):
    """
    Get all instances of model_class related to root_obj's graph.

    Args:
        model_class: The model to query (e.g., Documents, Annotations)
        root_obj: The root object to start traversal from
        user: Optional user for permission filtering via for_user()
        direction: 'down' for descendants, 'up' for ancestors
        include_types: Optional list of model classes to include in traversal
        exclude_types: Optional list of model classes to exclude from traversal

    Returns:
        QuerySet of model_class instances related to the graph
    """
    # Pass user to traversal for secure graph walking
    if direction == 'down':
        objects_by_type = get_descendants(
            root_obj, user=user,
            include_types=include_types, exclude_types=exclude_types
        )
    else:
        objects_by_type = get_ancestors(
            root_obj, user=user,
            include_types=include_types, exclude_types=exclude_types
        )

    q_filter = _build_generic_filter(objects_by_type)

    # Also filter the final result by user permissions
    if user and hasattr(model_class.objects, 'for_user'):
        return model_class.objects.for_user(user).filter(q_filter)

    return model_class.objects.filter(q_filter)
