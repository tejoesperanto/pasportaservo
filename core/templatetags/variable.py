import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


class VarNode(template.Node):
    """
    This tag stores its contents as an (optionally global) template variable.
    """

    def __init__(self, nodelist, name, is_global, is_trimmed):
        self.nodelist, self.var_name, self.var_is_global, self.trim_contents = nodelist, name, is_global, is_trimmed

    def render(self, context):
        result = self.nodelist.render(context)
        if self.trim_contents:
            result = mark_safe(result.strip())
        if self.var_is_global:
            context.dicts[0][self.var_name] = result
        else:
            context[self.var_name] = result
        return ''


class DeleteVarNode(template.Node):
    """
    This tag deletes an (optionally global) template variable, with one caveat:
    a global primitive such as 'True' is never deleted. Rather, its value is
    reset to the expected / original value.
    """

    def __init__(self, names, are_global):
        self.var_names, self.vars_are_global = names, are_global

    def render(self, context):
        if self.vars_are_global:
            primitives = {'True': True, 'False': False, 'None': None}
            for var_name in self.var_names:
                if var_name in primitives:
                    context.dicts[0][var_name] = primitives[var_name]
                else:
                    context.dicts[0].pop(var_name, None)
        else:
            for var_name in self.var_names:
                context.dicts[-1].pop(var_name, None)
        return ''


re_one_var = re.compile(r'(?:(global)\s+)?(?P<varname>\w+)(?:\s+(trimmed))?', re.DOTALL)
re_many_vars = re.compile(r'(?:(global)\s+)?(?P<varnames>\w+(?:\s+\w+)*)', re.DOTALL)


@register.tag(name='asvar')
def do_variable(parser, token):
    try:
        tag_name, arg = token.contents.split(maxsplit=1)
    except ValueError:
        raise template.TemplateSyntaxError("'%s' tag: Variable name is required" % token.contents)
    m = re_one_var.fullmatch(arg)
    if m:
        if m.group('varname').startswith('_'):
            raise template.TemplateSyntaxError(
                "'%s' tag: Variables may not begin with underscores: '%s'" % (tag_name, m.group('varname')))
        nodelist = parser.parse(('endasvar',))
        parser.delete_first_token()
        return VarNode(nodelist, name=m.group('varname'), is_global=m.group(1), is_trimmed=m.group(3))
    else:
        raise template.TemplateSyntaxError(
            "'%s' tag: Syntax is {%% asvar [global] var_name [trimmed] %%}" % tag_name)


@register.tag(name='delvar')
def undo_variable(parser, token):
    try:
        tag_name, args = token.contents.split(maxsplit=1)
    except ValueError:
        raise template.TemplateSyntaxError("'%s' tag: At least one variable name is required" % token.contents)
    m = re_many_vars.fullmatch(args)
    if m:
        var_list = m.group('varnames').split()
        if any(v.startswith('_') for v in var_list):
            raise template.TemplateSyntaxError(
                "'%s' tag: Variables may not begin with underscores" % tag_name)
        return DeleteVarNode(names=var_list, are_global=m.group(1))
    else:
        raise template.TemplateSyntaxError(
            "'%s' tag: Syntax is {%% delvar [global] var_name [var_name...] %%}" % tag_name)
