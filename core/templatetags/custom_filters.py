from django import template
from django.template.defaultfilters import filesizeformat

register = template.Library()

@register.filter
def format_file_size(value):
    """
    Formats the file size to be human readable.
    Overriding filesizeformat to use 'B' instead of 'bytes'.
    """
    if value < 1024:
        return f"{value} B"
    return filesizeformat(value)
