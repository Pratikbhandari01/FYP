from django import template
from django.apps import apps

register = template.Library()


@register.simple_tag
def get_model_count(app_label: str, model_name: str) -> int:
    """Return the number of objects for a given model.

    Usage:
        {% get_model_count "hotel" "hotel" as hotel_count %}
    """
    model = apps.get_model(app_label, model_name)
    if model is None:
        return 0
    return model.objects.count()
