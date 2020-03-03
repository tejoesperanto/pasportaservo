import string

from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, tag


@tag('templatetags')
class MakeVariableTagTests(TestCase):
    class DummyView(object):
        @property
        def simulate_role(self):
            return "ADMIN"

    @classmethod
    def setUpTestData(cls):
        cls.test_data = [
            ("Praesent congue erat at massa.", "Praesent congue erat at massa."),
            ("<img src='7.png' width=\"51\" />", "<img src='7.png' width=\"51\" />"),
            ("<script>alert(1); //&2^</script>", "<script>alert(1); //&2^</script>"),
            ("{{ view.simulate_role }}", "ADMIN"),
            ("{{ view.public_attr.0 }}", ""),
            ("{{ short_name|add:' ' }}", " "),
            ("<em>{{ long_var_name }}</em>", "<em>{}</em>".format(cls.__name__)),
            ("{{ True }}", "True"),
            ("~{{ _('Meenuu') }}~", "~Meenuu~"),
        ]

    @property
    def base_context(self):
        return {
            'long_var_name': self.__class__.__name__,
            'view': self.DummyView(),
        }

    def test_incorrect_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load variable %}{% asvar %}")
        self.assertIn("Variable name is required", str(cm.exception))

        for content in ("view.public_key", "42 + 24", "global ^X", "~~~ trimmed", "trimmed global"):
            with self.subTest(tag_content=content):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template(string.Template("{% load variable %}{% asvar $CONTENT %}").substitute(CONTENT=content))
                self.assertIn("Syntax is {% asvar", str(cm.exception))

        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load variable %}{% asvar test %}")
        self.assertIn("Unclosed tag on line 1: 'asvar'", str(cm.exception))

    def test_underscored_variable(self):
        for content in ("_x", "global _y", "_z trimmed", "global _A trimmed"):
            with self.subTest(tag_content=content):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template(string.Template("{% load variable %}{% asvar $CONTENT %}").substitute(CONTENT=content))
                self.assertIn("Variables may not begin with underscores", str(cm.exception))

    def test_stored_result(self):
        template_string_clear = string.Template(
            "{% load variable %} {% asvar test_var %}$TESTCONTENT{% endasvar %}")
        template_string_print = string.Template(
            "{% load variable %} {% asvar test_var %}$TESTCONTENT{% endasvar %}#{{ test_var }}#")

        for content, expected in self.test_data:
            with self.subTest(tag_content=content):
                template = Template(template_string_clear.substitute(TESTCONTENT=content))
                context = Context(self.base_context.copy())
                page = template.render(context)
                # Just storing the value in a context variable is expected to produce no output.
                self.assertEqual(page, " ")

                template = Template(template_string_print.substitute(TESTCONTENT=content))
                context = Context(self.base_context.copy())
                page = template.render(context)
                # Using the stored context variable is expected to produce output.
                self.assertEqual(page, " #{}#".format(expected))

    def test_stored_locally_result(self, is_global=False, is_builtin=False):
        template_string = string.Template("""
            {% load variable %}
            ^{{ $VARNAME }}^
            {% with local_context=True %}
                {% asvar $GLOBAL $VARNAME %}$TESTCONTENT{% endasvar %}
                #{{ $VARNAME }}#
            {% endwith %}
            *{{ $VARNAME }}*
        """)

        for var_name in ('test_var', 'qwe_rty_uio_p9', 'global') if not is_builtin else ('False', 'None'):
            for content, expected in self.test_data:
                with self.subTest(tag_content=content, var=var_name):
                    template = Template(template_string.substitute(
                        TESTCONTENT=content, VARNAME=var_name, GLOBAL="global" if is_global else "",
                    ))
                    context = Context(self.base_context.copy())
                    page = template.render(context)
                    self.assertEqual(
                        page.replace(" "*16, "").replace(" "*12, "").strip(),
                        "^{value_builtin}^\n\n\n#{value_local}#\n\n*{value_global}*".format(
                            value_local=expected,
                            value_builtin=var_name if is_builtin else "",
                            value_global=expected if is_global else (var_name if is_builtin else ""))
                    )

    def test_stored_globally_result(self):
        self.test_stored_locally_result(is_global=True)

    def test_builtin_override_locally(self):
        self.test_stored_locally_result(is_builtin=True)

    def test_builtin_override_globally(self):
        self.test_stored_locally_result(is_builtin=True, is_global=True)

    def test_trimmed_result(self):
        template_string = string.Template("""
            {% load variable %}
            ^{{ $VARNAME }}^
            {% asvar $VARNAME trimmed %}
                \r  $TESTCONTENT \t $TESTCONTENT  \v
            {% endasvar %}
            #{{ $VARNAME }}#
        """)

        for var_name, var_override in (('test_var', False),
                                       ('long_var_name', True),
                                       ('global_', False),
                                       ('None', True)):
            for content, expected in self.test_data:
                with self.subTest(tag_content=content, var=var_name):
                    template = Template(template_string.substitute(
                        TESTCONTENT=content, VARNAME=var_name,
                    ))
                    context = Context(self.base_context.copy())
                    original_value = context[var_name] if var_override else ""
                    page = template.render(context)
                    self.assertEqual(
                        page.replace(" "*12, "").strip(),
                        "^{value_before}^\n\n#{value_after}#".format(
                            value_before=original_value,
                            value_after="{0} \t {0}".format(expected) if expected.strip() != "" else "")
                    )

    def test_confusing_variable(self):
        combinations = (
            # A combination of 'global global trimmed' is expected to produce a variable
            # named 'global' in the top-level context, with whitespace in contents removed.
            ('global global trimmed',
             lambda v: {'local_full_var': v if v.strip() else "",
                        'local_trim_var': "",
                        'global_full_var': v if v.strip() else "",
                        'global_trim_var': ""}),
            # A combination of 'global trimmed trimmed' is expected to produce a variable
            # named 'trimmed' in the top-level context, with whitespace in contents removed.
            ('global trimmed trimmed',
             lambda v: {'local_full_var': "",
                        'local_trim_var': v if v.strip() else "",
                        'global_full_var': "",
                        'global_trim_var': v if v.strip() else ""}),
            # A combination of 'global global' is expected to produce a variable
            # named 'global' in the top-level context, with whitespace in contents preserved.
            ('global global',
             lambda v: {'local_full_var': "\n{s1}{content}\n{s2}".format(content=v, s1=" "*28, s2=" "*24),
                        'local_trim_var': "",
                        'global_full_var': "\n{s1}{content}\n{s2}".format(content=v, s1=" "*28, s2=" "*24),
                        'global_trim_var': ""}),
            # A combination of 'trimmed trimmed' is expected to produce a variable
            # named 'trimmed' in the bottom-level context, with whitespace in contents removed.
            ('trimmed trimmed',
             lambda v: {'local_full_var': "",
                        'local_trim_var': v if v.strip() else "",
                        'global_full_var': "",
                        'global_trim_var': ""}),
            # A combination of 'global trimmed' is expected to produce a variable
            # named 'trimmed' in the top-level context, with whitespace in contents preserved.
            ('global trimmed',
             lambda v: {'local_full_var': "",
                        'local_trim_var': "\n{s1}{content}\n{s2}".format(content=v, s1=" "*28, s2=" "*24),
                        'global_full_var': "",
                        'global_trim_var': "\n{s1}{content}\n{s2}".format(content=v, s1=" "*28, s2=" "*24)}),
        )

        for combi, expected_vars in combinations:
            with self.subTest(combi=combi):
                template_string = string.Template("""
                    {% load variable %}
                    {% with local_context=True %}
                        {% asvar $COMBINATION %}
                            $TESTCONTENT
                        {% endasvar %}
                        ^{{ global }}^@{{ trimmed }}@
                    {% endwith %}
                    #{{ global }}#*{{ trimmed }}*
                """)
                for content, expected in self.test_data:
                    with self.subTest(tag_content=content):
                        template = Template(template_string.substitute(COMBINATION=combi, TESTCONTENT=content))
                        context = Context(self.base_context.copy())
                        page = template.render(context)
                        self.assertEqual(
                            page.strip(),
                            "^{local_full_var}^@{local_trim_var}@"
                            "{space}"
                            "#{global_full_var}#*{global_trim_var}*".format(
                                space=("\n"+" "*20)*2, **expected_vars(expected))
                        )


@tag('templatetags')
class DeleteVariableTagTests(TestCase):
    test_value = "Praesent congue erat at massa."

    def test_incorrect_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load variable %}{% delvar %}")
        self.assertIn("At least one variable name is required", str(cm.exception))

        for content in ("view.public_key", "42 + 24", "global ^X", "~~~ trimmed", "trimmed:global"):
            with self.subTest(tag_content=content):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template(string.Template("{% load variable %}{% delvar $CONTENT %}").substitute(CONTENT=content))
                self.assertIn("Syntax is {% delvar", str(cm.exception))

        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load variable %}{% delvar test %}{% enddelvar %}")
        self.assertIn("Invalid block tag on line 1: 'enddelvar'", str(cm.exception))

    def test_underscored_variables(self):
        for content in ("_x", "x _y z", "global _A", "_b _trimmed", "global c trimmed _"):
            with self.subTest(tag_content=content):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template(string.Template("{% load variable %}{% delvar $CONTENT %}").substitute(CONTENT=content))
                self.assertIn("Variables may not begin with underscores", str(cm.exception))

    def test_one_variable(self):
        template_string = """
            {% load variable %}
            ^{{ test }}^
            {% delvar test %}
            #{{ test }}#
        """
        template = Template(template_string)
        context = Context({'test': self.test_value})
        page = template.render(context)
        self.assertEqual(
            page.strip(),
            "^{value_before}^{space}#{value_after}#".format(
                value_before=self.test_value,
                value_after="",
                space=("\n"+" "*12)*2)
        )

    def test_existing_variable(self):
        template_string = """
            {% load variable %}
            ^{{ testA }}^{{ testB }}^{{ testC }}^
            {% delvar testB %}
            #{{ testA }}#{{ testB }}#{{ testC }}#
        """
        template = Template(template_string)
        context = Context({'testA': self.test_value, 'testB': "<script>alert(2);", 'testC': self.test_value})
        page = template.render(context)
        self.assertEqual(
            page.strip(),
            "^{value_a_before}^{value_b_before}^{value_c_before}^"
            "{space}"
            "#{value_a_after}#{value_b_after}#{value_c_after}#".format(
                value_a_before=self.test_value,
                value_a_after=self.test_value,
                value_b_before="&lt;script&gt;alert(2);",
                value_b_after="",
                value_c_before=self.test_value,
                value_c_after=self.test_value,
                space=("\n"+" "*12)*2)
        )

    def test_nonexistent_variable(self):
        template_string = """
            {% load variable %}
            ^{{ testA }}^{{ testB }}^
            {% delvar testB %}
            #{{ testA }}#{{ testB }}#
        """
        template = Template(template_string)
        context = Context({'testA': self.test_value})
        page = template.render(context)
        self.assertEqual(
            page.strip(),
            "^{content}^^{space}#{content}##".format(content=self.test_value, space=("\n"+" "*12)*2)
        )

    def test_variable_in_local_context(self):
        template_string = """
            {% load variable %}
            {% with local_context=True %}
                {% delvar test %}
            {% endwith %}
            #{{ test }}#
        """
        template = Template(template_string)
        context = Context({'test': self.test_value})
        page = template.render(context)
        self.assertEqual(page.strip(), "#{content}#".format(content=self.test_value))

    def test_many_variables(self):
        template_string = """
            {% load variable %}
            ^{{ testA }}^{{ testB }}^{{ testC }}^
            {% delvar testC testD testA testB testA %}
            #{{ testA }}#{{ testB }}#{{ testC }}#
        """
        template = Template(template_string)
        context = Context({'testA': self.test_value, 'testB': self.test_value, 'testC': self.test_value})
        page = template.render(context)
        self.assertEqual(
            page.strip(),
            "^{value_before}^{value_before}^{value_before}^{space}####".format(
                value_before=self.test_value,
                space=("\n"+" "*12)*2)
        )

    def test_global_variable(self):
        template_string = """
            {% load variable %}
            ^{{ testA }}^{{ True }}^{{ testB }}^
            {% with local_context=True %}
                {% delvar global testB testA %}
            {% endwith %}
            #{{ testA }}#{{ True }}#{{ testB }}#
        """
        template = Template(template_string)
        context = Context({'testB': self.test_value})  # A value in a middle-level context.
        context.dicts[0]['testA'] = self.test_value  # A value in the top-level context.
        page = template.render(context)
        self.assertEqual(
            " ".join(page.split()),
            "^{content}^True^{content}^ ##True#{content}#".format(content=self.test_value)
        )

    def test_builtin_variable(self):
        # Removal of a global built-in value (True, False, None) is expected to restore the original value.
        template_string = string.Template("""
            {% load variable i18n %}
            ^{{ $BUILTIN }}^
            {% trans "Praesent turpis." as $BUILTIN %}
            *{{ $BUILTIN }}*
            {% delvar $BUILTIN %}
            @{{ $BUILTIN }}@
            {% delvar $BUILTIN %}
            @{{ $BUILTIN }}@
            {% delvar global $BUILTIN %}
            #{{ $BUILTIN }}#
        """)
        for builtin in ('True', 'False', 'None'):
            with self.subTest(builtin=builtin):
                template = Template(template_string.substitute(BUILTIN=builtin))
                context = Context({})
                context.dicts[0][builtin] = "Totoro"  # Simulate an overriden global built-in.
                page = template.render(context)
                self.assertEqual(
                    " ".join(page.split()),
                    "^Totoro^ *Praesent turpis.* @Totoro@ @Totoro@ #{}#".format(builtin)
                )

    def test_confusing_variable(self):
        # The usage of 'global' is expected to remove a variable called "global" from
        # the context, if such variable exists.
        template = Template("{% load variable %}{% delvar global %}{{ global }}")

        context = Context({})
        self.assertNotIn('global', context)
        page = template.render(context)
        self.assertNotIn('global', context)
        self.assertEqual(page, "")

        context = Context({'global': self.test_value})
        self.assertIn('global', context)
        page = template.render(context)
        self.assertNotIn('global', context)
        self.assertEqual(page, "")

        # The usage of 'global global' is expected to remove a variable called "global" from
        # the top-level context, but not other levels of the context, if such variable exists.
        template = Template("{% load variable %}{% delvar global global %}{{ global }}")

        context = Context({})
        self.assertNotIn('global', context)
        page = template.render(context)
        self.assertNotIn('global', context)
        self.assertEqual(page, "")

        context = Context({'global': self.test_value})
        self.assertIn('global', context)
        page = template.render(context)
        self.assertIn('global', context)
        self.assertEqual(page, self.test_value)

        context = Context({})
        context.dicts[0]['global'] = "Satsuki"  # Simulate a variable in the top-level context.
        self.assertIn('global', context)
        page = template.render(context)
        self.assertNotIn('global', context)
        self.assertEqual(page, "")
