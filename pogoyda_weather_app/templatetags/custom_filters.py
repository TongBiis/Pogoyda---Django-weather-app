from django import template

register = template.Library()

@register.filter
def first_word(value, separator=' '):

    if not value:
        return ''
    return value.split(separator)[0]