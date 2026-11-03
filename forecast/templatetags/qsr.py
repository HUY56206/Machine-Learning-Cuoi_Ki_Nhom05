from django import template

register = template.Library()


@register.filter
def thousands(value):
    """1234567 -> 1.234.567 (định dạng Việt Nam)."""
    try:
        return f'{int(round(float(value))):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return value


@register.filter
def dm(value, fmt='%d/%m/%Y'):
    return value.strftime(fmt) if value else ''


@register.filter
def initial(value):
    return (str(value)[:1] or '?').upper()
