from django import template

register = template.Library()

@register.filter
def make_list(value):
    """Convert a string to a list of characters."""
    return list(str(value))