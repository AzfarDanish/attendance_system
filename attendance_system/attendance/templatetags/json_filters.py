from django import template
import json as json_module

register = template.Library()

@register.filter
def to_json(value):
    return json_module.dumps(value)