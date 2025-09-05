from django import template
import datetime

register = template.Library()

@register.filter
def to_local_date(value, format_string='%Y/%m/%d'):
    if not value:
        return ''
    
    if isinstance(value, datetime.datetime):
        return value.strftime(format_string)
    elif isinstance(value, datetime.date):
        return value.strftime(format_string)
    else:
        return value 