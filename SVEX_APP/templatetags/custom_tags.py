from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name="add_class")
def add_class(value, arg):
    return value.as_widget(attrs={"class": arg})

@register.filter(name="mul")
def mul(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except Exception:
        return 0


@register.filter(name="usd")
def usd(value):
    try:
        return f"{Decimal(str(value)):.2f}"
    except Exception:
        return "0.00"