from django import template

register = template.Library()

@register.filter
def make_list(value):
    """Convert a string to a list of characters."""
    return list(str(value))

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)
