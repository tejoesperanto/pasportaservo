import re

from django import template

register = template.Library()


class VarNode(template.Node):
    """
    This tag stores its contents as an (optionally global) template variable.
    """

    def __init__(self, nodelist, name, is_global):
        self.nodelist, self.var_name, self.var_is_global = nodelist, name, is_global

    def render(self, context):
        result = self.nodelist.render(context)
        if self.var_is_global:
            context.dicts[0][self.var_name] = result
        else:
            context[self.var_name] = result
        return ''


re_var = re.compile(r'(?:(global)\s+)?(\w+)', re.DOTALL)


@register.tag(name='asvar')
def do_variable(parser, token):
    try:
        tag_name, arg = token.contents.split(maxsplit=1)
    except ValueError:
        raise template.TemplateSyntaxError("'%s' tag: Variable name is required" % token.contents)
    m = re_var.fullmatch(arg)
    if m:
        nodelist = parser.parse(('endasvar',))
        parser.delete_first_token()
        return VarNode(nodelist, name=m.group(2), is_global=m.group(1))
    else:
        raise template.TemplateSyntaxError("'%s' tag: Syntax is {%% asvar [global] var_name %%}" % tag_name)
