from django import template
import markdown2
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def dict_get(d, key_path):
    """
    Access dictionary with dot notation for nested keys
    Example: {{ results|dict_get:quiz.id.selected }}
    """
    if not d:
        return None
        
    if '.' in key_path:
        main_key, sub_key = key_path.split('.', 1)
        try:
            if isinstance(main_key, str) and main_key.isdigit():
                main_key = int(main_key)
            return dict_get(d.get(main_key), sub_key)
        except (KeyError, AttributeError):
            return None
    try:
        if isinstance(key_path, str) and key_path.isdigit():
            key_path = int(key_path)
        return d.get(key_path)
    except (KeyError, AttributeError):
        return None

@register.filter
def get_item(dictionary, key):
    """Simple dictionary lookup"""
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def markdown(text):
    """Convert markdown text to HTML"""
    if not text:
        return ""
    # Convert markdown to HTML with extra features enabled
    html = markdown2.markdown(text, extras=[
        "fenced-code-blocks", 
        "tables", 
        "header-ids", 
        "task-lists", 
        "code-friendly"
    ])
    return mark_safe(html)  # Mark as safe to prevent HTML escaping
