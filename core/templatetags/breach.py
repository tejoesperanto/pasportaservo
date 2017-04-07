from django import template
import random

register = template.Library()


@register.simple_tag
def random_identifier(length=None):
    try:
        length = int(length)
    except:
        length = None
    if length is None or length <= 0:
        length = random.randint(16, 48)
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789_') for n in range(length))
