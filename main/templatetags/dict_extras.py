from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """Достает значение из словаря по ключу: {{ my_dict|dict_get:key_var }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None