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


@register.simple_tag
def get_recent_records(app_label: str, model_name: str, limit: int = 5):
    """Return a queryset of recent model rows ordered by newest first."""
    model = apps.get_model(app_label, model_name)
    if model is None:
        return []

    order_field = '-id'
    if hasattr(model, 'date'):
        order_field = '-date'
    elif hasattr(model, 'created_at'):
        order_field = '-created_at'

    return model.objects.all().order_by(order_field)[:limit]
