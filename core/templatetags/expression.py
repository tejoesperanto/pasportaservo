# https://gist.github.com/aliang/773650

import logging
import re
from collections import namedtuple

from django import template
from django.utils.translation import gettext_lazy

register = template.Library()

expr_log = logging.getLogger('PasportaServo.expr')


class ExprNode(template.Node):
    """
    This tag can be used to calculate an arbitrary python expression,
    because Django is obnoxious about having you not calculate things.

    To save result in another template variable:
    {% expr "1" as var1 %}
    {% expr [0, 1, 2] as var2 %}
    {% expr _('Menu') as var3 %}
    {% expr var1 + "abc" as var4 %}

    To directly output result:
    {% expr 3 %}
    {% expr "".join(["a", "b", "c"]) %}

    Syntax:
    {% expr python_expression as [global] variable_name %}
    {% expr python_expression %}

    python_expression can be any valid python expression, and you can
    even use _() to translate a string. {% expr %} tag also has access
    to context variables. it is advised to NEVER include any client-
    influenced values since those can cause a server-side injection.
    """

    def __init__(self, expr_string, variable):
        self.expr_string, self.variable = expr_string, variable

    def render(self, context):
        try:
            d = context.flatten()
            d['_'] = gettext_lazy
            result = eval(self.expr_string, d)
            expr_log.debug("Evaluated [ %s ] resulting in [ %r ]", self.expr_string, result)
            if self.variable:
                if self.variable.is_global:
                    context.dicts[0][self.variable.name] = result
                else:
                    context[self.variable.name] = result
                return ""
            else:
                return result
        except Exception:
            expr_log.warning("Expression invalid: [ %s ]", self.expr_string)
            return ""


re_expr = re.compile(r'(.*?)\s+as\s+(?:(global)\s+)?(\w+)', re.DOTALL)


@register.tag(name='expr')
def do_expr(parser, token):
    try:
        tag_name, arg = token.contents.split(maxsplit=1)
    except ValueError:
        raise template.TemplateSyntaxError("'%s' tag: Expression is required" % token.contents)
    m = re_expr.fullmatch(arg)
    if m:
        expr_string = m.group(1)
        var = namedtuple('Variable', 'name, is_global')(m.group(3), m.group(2))
    else:
        expr_string, var = arg, None
    return ExprNode(expr_string, var)
