import logging
import string

from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, tag


@tag('templatetags')
class ExpressionTagTests(TestCase):
    _sentinel = {'T': 'F', 'r': 'R', 'u': 'A', 't': 'U', 'h': 'D'}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.logger = logging.getLogger('PasportaServo.expr')
        cls.logger.setLevel(logging.CRITICAL)

    @classmethod
    def setUpTestData(cls):
        cls.test_data = [
            ("13.7", "13.7", False),
            (15.8, "15.8", False),
            ("\"Abc\"", "Abc", False),
            (True, "True", False),
            ("varONE", "", True),
            ("request.user", "", True),
            ("view.public_attr.0", "", True),
            ("view._private_attr.strip", "", True),
            ("view._sentinel", str(cls._sentinel), False),
            ("view.__class__.__name__", cls.__name__, False),
            ("varTWO", cls.__name__, False),
            ("varTWO[-5:]", "Tests", False),
            ("_('Menu')", "Menu", False),
            ("'|'.join(['a', 'b', 'c'])", "a|b|c", False),
            ("str(type(view))[1:str(type(view)).find(' ')].upper()", "CLASS", False),
            ("[1, 0, 7].express()", "", True),
        ]

    @property
    def base_context(self):
        return {
            'varTWO': self.__class__.__name__,
            'view': self,
        }

    @property
    def more_context(self):
        return {
            'WIZARD': 1.3,
            'ELF': 0.8,
        }

    def test_incorrect_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load expression %}{% expr %}")
        self.assertIn("Expression is required", str(cm.exception))

    def test_incorrect_var_name(self):
        template = Template("{% load expression %}{% expr 42 + 24 as view.secret_key %}")
        with self.assertLogs(self.logger, logging.WARNING):
            page = template.render(Context({}))
        self.assertEqual(page, "")

    def test_immediate_result(self):
        template_string = string.Template("{% load expression %}[{% expr $TESTEXPR %}]")
        for expr, expected, should_emit_log in self.test_data:
            with self.subTest(expr=expr):
                template = Template(template_string.substitute(TESTEXPR=expr))
                context = Context(self.base_context.copy())
                context.update(self.more_context.copy())
                if should_emit_log:
                    with self.assertLogs(self.logger, logging.WARNING):
                        page = template.render(context)
                else:
                    page = template.render(context)
                self.assertEqual(page, "[{}]".format(expected))

    def test_stored_result(self):
        template_string_clear = string.Template(
            "{% load expression %} {% expr $TESTEXPR as test_var %}")
        template_string_print = string.Template(
            "{% load l10n expression %} {% expr $TESTEXPR as test_var %}"
            "{% localize off %}#{{ test_var|safe }}#{% endlocalize %}")

        for expr, expected, should_emit_log in self.test_data:
            with self.subTest(expr=expr):
                template = Template(template_string_clear.substitute(TESTEXPR=expr))
                context = Context(self.base_context.copy())
                if should_emit_log:
                    with self.assertLogs(self.logger, logging.WARNING):
                        page = template.render(context)
                else:
                    page = template.render(context)
                # Just storing the value in a context variable is expected to produce no output.
                self.assertEqual(page, " ")

                template = Template(template_string_print.substitute(TESTEXPR=expr))
                context = Context(self.base_context.copy())
                page = template.render(context)
                # Using the stored context variable is expected to produce output.
                self.assertEqual(page, " #{}#".format(expected))

    def test_stored_locally_result(self, is_global=False):
        template_string = string.Template("""
            {% load l10n expression %}{% localize off %}
            ^{{ $VARNAME|safe }}^
            {% with local_context=True %}
                {% expr $TESTEXPR as $GLOBAL $VARNAME %}
                #{{ $VARNAME|safe }}#
            {% endwith %}
            *{{ $VARNAME|safe }}*
            {% endlocalize %}
        """)

        for var_name in ('test_var', 'qwe_rty_uio_p8', 'global'):
            for expr, expected, should_emit_log in self.test_data:
                with self.subTest(expr=expr, var=var_name):
                    template = Template(template_string.substitute(
                        TESTEXPR=expr, VARNAME=var_name, GLOBAL="global" if is_global else "",
                    ))
                    context = Context(self.base_context.copy())
                    page = template.render(context)
                    self.assertEqual(
                        page.replace(" "*16, "").replace(" "*12, "").strip(),
                        "^^\n\n\n#{value_local}#\n\n*{value_global}*".format(
                            value_local=expected, value_global=expected if is_global else "")
                    )

    def test_stored_globally_result(self):
        self.test_stored_locally_result(is_global=True)
