from django import template

register = template.Library()


@register.filter
def get(d, key):
    """模板里对 dict 按 key 取值：{{ mydict|get:"politics" }}"""
    try:
        return d.get(key)
    except AttributeError:
        return None
