from django import template
from django.template.defaultfilters import urlencode

register = template.Library()

@register.filter
def get_attr(obj, attr):
    """Resolve nested attributes like 'part_type__name'."""
    try:
        for part in attr.split("__"):
            obj = getattr(obj, part)
        return obj
    except Exception:
        return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def without_key(dict_obj, key):
    """Remove a key from a dict for clean URL construction"""
    return {k: v for k, v in dict_obj.items() if k != key}

@register.filter
def safe_urlencode(value):
    """URL-encode a dict"""
    return urlencode(value)


@register.filter(name='abs')
def abs_filter(value):
    """Return absolute value of a number."""
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value