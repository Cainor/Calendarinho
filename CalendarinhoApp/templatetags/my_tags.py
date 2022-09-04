from django import template

register = template.Library()

@register.filter
def return_engName(l, i):
    try:
        return l[i].EngName
    except:
        return ""

@register.filter
def return_id(l, i):
    try:
        return l[i].id
    except:
        return ""