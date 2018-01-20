import logging
import re

from django import template

register = template.Library()

privacy_log = logging.getLogger('PasportaServo.privacy')


@register.tag(name='if-visible')
def if_visible(parser, token):
    """
    A template tag with the semantics of 'if', for verifying if an object should be displayed according to its
    visibility settings.
    Syntax:
        {% if-visible object [attribute] {privileged=(True|False)} {store} %}...{% endif %}
    The result can optionally be saved into a context variable, by using the `store` parameter. In this case,
    a `shall_display_<attribute-name>` or `shall_display_<object-name>` will be available later in the template.
    """
    nodelist = parser.parse(('endif',))
    parser.delete_first_token()
    bits = token.split_contents()
    syntax = (r'(?P<obj>[^ ]+?)'
              r'(?: \[(?P<attr>[^ ]+?)\])?'
              r'(?: privileged=(?P<priv_ctx>[^ ]+?))?'
              r'(?: (?P<as_var>store))?')
    m = re.fullmatch(syntax.replace(' ', '\x00'), '\x00'.join(bits[1:]))
    if not m:
        raise template.TemplateSyntaxError(
            "'%s' tag: Incorrectly provided arguments. "
            "Expected object [, \"[\"sub-object\"]\"] [, privileged=(True|False)] [, store]."
            % bits[0]
        )
    return DisplayGovernorNode(
        nodelist,
        parser.compile_filter(m.group('obj')),
        m.group('attr') and parser.compile_filter(m.group('attr')),
        parser.compile_filter(m.group('priv_ctx') or ''),
        bool(m.group('as_var'))
    )


class DisplayGovernorNode(template.Node):
    def __init__(self, nodelist, obj, attr=None, priv_ctx=False, as_var=False):
        self.nodelist = nodelist
        self.object = obj
        self.attribute = attr
        self.privilege_context = priv_ctx
        self.as_var = as_var

    def render(self, context):
        if 'user' not in context or not context['user'].is_authenticated:
            return ''

        var = self.object.resolve(context)
        subvar = self.attribute.resolve(context) if self.attribute else None
        if self.attribute and not subvar:
            if re.fullmatch(r'\w+', self.attribute.token):
                subvar = self.attribute.token
        if self.attribute and not subvar:
            raise AttributeError(
                "'{}' did not resolve to any name of attribute on {}"
                .format(self.attribute, var._meta.model.__name__)
            )
        is_privileged = bool(self.privilege_context.resolve(context))

        visibility = getattr(var, ('{}_'.format(subvar) if subvar else '') + 'visibility')
        result = visibility.visible_online_public or (is_privileged and visibility.visible_online_authed)
        privacy_log.debug(
            "%r%s\r (OP:%r | C:%r & OA:%r) = %r",
            var, ".%s" % subvar if subvar else "",
            visibility.visible_online_public, is_privileged, visibility.visible_online_authed, result)
        if self.as_var:
            output_var = 'shall_display_{}'.format((subvar if subvar else var._meta.model.__name__).lower())
            context[output_var] = result
        return self.nodelist.render(context) if result else ''
