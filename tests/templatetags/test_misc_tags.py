import string
import sys
import unittest
from collections import namedtuple

from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, tag
from django.utils.functional import SimpleLazyObject
from django.utils.html import escape

from faker import Faker


@tag('templatetags')
class RandomIdentifierTagTests(TestCase):
    template_string = string.Template("{% load random_identifier from utils %}{% random_identifier $LENGTH %}")
    re_default = r'^[A-Za-z1-9_]{16,48}$'

    def test_no_length(self):
        template = Template(self.template_string.substitute(LENGTH=""))
        page = template.render(Context())
        self.assertRegex(page, self.re_default)

    def test_invalid_length(self):
        for length in ("aaabbbcc", -6, -12.34, "qwerty1sadf", 0, "view.non_existent_attr"):
            with self.subTest(id_len=length):
                template = Template(self.template_string.substitute(LENGTH=length))
                page = template.render(Context())
                self.assertRegex(page, self.re_default)

    def test_valid_length(self):
        for length in range(1, 200):
            with self.subTest(id_len=length):
                template = Template(self.template_string.substitute(LENGTH=length))
                page = template.render(Context())
                self.assertRegex(page, r'^[A-Za-z1-9_]{%d}$' % length)


@tag('templatetags')
class PublicIdFilterTests(TestCase):
    template_string = "{% load public_id from utils %}{{ my_obj|public_id }}"

    def test_invalid_object(self):
        for obj in (255,
                    "zxcvbn",
                    namedtuple('ObjectWithPk', 'pk')(pk=1023),
                    namedtuple('ObjectWithDate', 'date_joined')(date_joined="2011-02-03")):
            with self.subTest(obj=obj):
                page = Template(self.template_string).render(Context({'my_obj': obj}))
                self.assertEquals(page, "")

    def test_valid_object(self):
        Cls = namedtuple('ObjectWithFields', 'pk, name, date_joined, date_deleted')
        obj = Cls(pk=1023, name="John", date_joined="2011-02-03", date_deleted="2018-07-06")
        with self.subTest(obj=obj):
            page = Template(self.template_string).render(Context({'my_obj': obj}))
            self.assertEquals(page, "d64d289bce1a4d5a355bf948a58af770842a008d74bd375f57d182375838994c")

        faker = Faker()
        first_obj = Cls(
            pk=faker.pyint(),
            name=faker.first_name(),
            date_joined=faker.past_date(),
            date_deleted=faker.future_date())
        hash_of_obj = ""
        object_list = [first_obj]
        for i in range(15):
            obj = Cls(
                pk=first_obj.pk,
                date_joined=first_obj.date_joined,
                name=faker.first_name(),
                date_deleted=faker.future_date())
            object_list.append(obj)
        for obj in object_list:
            with self.subTest(obj=obj):
                page = Template(self.template_string).render(Context({'my_obj': obj}))
                self.assertRegex(page, r'^[a-f0-9]{64}$')
                if obj is first_obj:
                    hash_of_obj = page
                else:
                    self.assertEqual(page, hash_of_obj)


@tag('templatetags')
class ListTagTests(TestCase):
    def test_list_output_empty(self):
        # Empty parameter list is expected to result in an empty list.
        page = Template("{% load list from utils %}{% list %}").render(Context())
        self.assertEqual(page, "[]")

    def test_list_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load list from utils %}{% list a=33 b=22 c=11 %}")
        self.assertIn("unexpected keyword argument", str(cm.exception))

    def test_list_output(self):
        # A list of parameters is expected to result in a list containing those parameters.
        page = Template("{% load list from utils %}{% list 'aa' +2 'bb' -2 'cc' %}").render(Context())
        self.assertEqual(page, "[&#39;aa&#39;, 2, &#39;bb&#39;, -2, &#39;cc&#39;]")

        page = Template(
            "{% load list from utils %}"
            "{% autoescape off %}{% list 'aa' +2 'bb' -2 'cc' %}{% endautoescape %}"
        ).render(Context())
        self.assertEqual(page, "['aa', 2, 'bb', -2, 'cc']")

    def test_list_result_empty(self):
        # Empty parameter list is expected to result in an empty list.
        page = Template(
            "{% load list from utils %}{% list as L %}{% for x in L %}[{{ x }}]{% endfor %}"
        ).render(Context())
        self.assertEqual(page, "")

    def test_list_result(self):
        # A list of parameters is expected to result in a list containing those parameters.
        # When parameters are safe, they are expected to not be encoded on output.
        page = Template("""
            {% load list from utils %}
            {% list 'a<a' +2 'b>b' -2 'c&c' as L %}
            {% for x in L %}[{{ x }}],{% endfor %}
        """).render(Context())
        self.assertEqual(page.strip(), "[a<a],[2],[b>b],[-2],[c&c],")

        # A list of parameters is expected to result in a list containing those parameters.
        # When parameters are not safe, they are expected to be encoded on output depending
        # on the 'autoescape' tag.
        template_string = string.Template("""
            {% load list from utils %}
            {% autoescape $SWITCH %}
                {% list AA +2 BB -2 CC as L %}
                {% for x in L %}[{{ x }}],{% endfor %}
            {% endautoescape %}
        """)
        expected_value = {
            'on': "[A&lt;a],[2],[b&gt;B],[-2],[C&amp;c],",
            'off': "[A<a],[2],[b>B],[-2],[C&c],",
        }
        for switch in ('on', 'off'):
            with self.subTest(autoescape=switch):
                template = Template(template_string.substitute(SWITCH=switch))
                page = template.render(Context({'CC': "C&c", 'BB': "b>B", 'AA': "A<a"}))
                self.assertEqual(page.strip(), expected_value[switch])


@tag('templatetags')
class DictTagTests(TestCase):
    def test_dict_output_empty(self):
        # Empty parameter list is expected to result in an empty dict.
        page = Template("{% load dict from utils %}{% dict %}").render(Context())
        self.assertEqual(page, "{}")

    def test_dict_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load dict from utils %}{% dict 1 2 3 %}")
        self.assertIn("too many positional arguments", str(cm.exception))

    @unittest.skipIf(sys.version_info < (3, 6), 'Order of dict cannot be guaranteed in Py < 3.6')
    def test_dict_output(self):
        # A list of parameters is expected to result in a dict containing those keys and values.
        page = Template("{% load dict from utils %}{% dict aa=True bb=False cc=None %}").render(Context())
        self.assertEqual(page, "{&#39;aa&#39;: True, &#39;bb&#39;: False, &#39;cc&#39;: None}")

        page = Template(
            "{% load dict from utils %}"
            "{% autoescape off %}{% dict aa=+2 bb=-2 cc=33 %}{% endautoescape %}"
        ).render(Context())
        self.assertEqual(page, "{'aa': 2, 'bb': -2, 'cc': 33}")

    def test_dict_result_empty(self):
        # Empty parameter list is expected to result in an empty dict.
        page = Template(
            "{% load dict from utils %}{% dict as D %}"
            "{% for x, y in D.items %}[{{ x }}:{{ y }}]{% endfor %}"
        ).render(Context())
        self.assertEqual(page, "")

    @unittest.skipIf(sys.version_info < (3, 6), 'Order of dict cannot be guaranteed in Py < 3.6')
    def test_dict_result(self):
        # A list of parameters is expected to result in a dict containing those keys and values.
        # When values are safe, they are expected to not be encoded on output.
        page = Template("""
            {% load dict from utils %}
            {% dict a='+2' b='-2' c='33' as D %}
            {% for x in D %}[{{ x }}],{% endfor %};
            {% for x, y in D.items %}[{{ x }}={{ y }}],{% endfor %}.
        """).render(Context())
        self.assertEqual(page.strip(), "[a],[b],[c],;\n{}[a=+2],[b=-2],[c=33],.".format(' '*12))

        # A list of parameters is expected to result in a dict containing those keys and values.
        # When values are not safe, they are expected to be encoded on output depending on the
        # 'autoescape' tag.
        template_string = string.Template("""
            {% load dict from utils %}
            {% autoescape $SWITCH %}
                {% dict a=AA b=BB c=CC as D %}
                {% for x in D %}[{{ x }}],{% endfor %};
                {% for x, y in D.items %}[{{ forloop.counter }}:{{ x }}={{ y }}],{% endfor %}.
            {% endautoescape %}
        """)
        expected_value = {
            'on': "[a],[b],[c],;\n{}[1:a=A&lt;a],[2:b=b&gt;B],[3:c=C&amp;c],.".format(' '*16),
            'off': "[a],[b],[c],;\n{}[1:a=A<a],[2:b=b>B],[3:c=C&c],.".format(' '*16),
        }
        for switch in ('on', 'off'):
            with self.subTest(autoescape=switch):
                template = Template(template_string.substitute(SWITCH=switch))
                page = template.render(Context({'CC': "C&c", 'BB': "b>B", 'AA': "A<a"}))
                self.assertEqual(page.strip(), expected_value[switch])


@tag('templatetags')
class AnyFilterTests(TestCase):
    template = Template("{% load are_any from utils %}{{ my_var|are_any }}")

    def test_iterable(self):
        test_data = [
            ([], False),
            ({}, False),
            ([0, None, ""], False),
            ([0, None, "", object], True),
            (["", "", "", "4", ""], True),
            ((x for x in ["", False, "", False, ""]), False),
            ((y for y in ["", False, "4", True, ""]), True),
            ({"": 1, None: 3}, False),
            (" \n \0", True),
            ("abcdef", True),
        ]
        for obj, expected_value in test_data:
            with self.subTest(object=obj):
                page = self.template.render(Context({'my_var': obj}))
                self.assertEqual(page, str(expected_value))

    def test_non_iterable(self):
        test_data = [
            (1, True),
            (0, False),
            (True, True),
            (None, False),
            (object, True),
            (SimpleLazyObject(lambda: None), False),
            (SimpleLazyObject(lambda: "LLZ"), True),
        ]
        for obj, expected_value in test_data:
            with self.subTest(object=obj):
                page = self.template.render(Context({'my_var': obj}))
                self.assertEqual(page, str(expected_value))


@tag('templatetags')
class AllFilterTests(TestCase):
    template = Template("{% load are_all from utils %}{{ my_var|are_all }}")

    def test_iterable(self):
        test_data = [
            ([], True),
            ({}, True),
            ([0, None, ""], False),
            ([1, True, "\0"], True),
            ([0, None, "", object], False),
            (["", "", "", "4", ""], False),
            ([object], True),
            ((x for x in ["1", True, "22", None, "33"]), False),
            ((y for y in ["1", 2, "3", 4, "5", object]), True),
            ({"": 1, None: 3}, False),
            ({"a": 1, True: 3}, True),
            ("", True),
            (" \n \0", True),
            ("abcdef", True),
        ]
        for obj, expected_value in test_data:
            with self.subTest(object=obj):
                page = self.template.render(Context({'my_var': obj}))
                self.assertEqual(page, str(expected_value))

    def test_non_iterable(self):
        test_data = [
            (1, True),
            (0, False),
            (True, True),
            (None, False),
            (object, True),
            (SimpleLazyObject(lambda: None), False),
            (SimpleLazyObject(lambda: "LLZ"), True),
        ]
        for obj, expected_value in test_data:
            with self.subTest(object=obj):
                page = self.template.render(Context({'my_var': obj}))
                self.assertEqual(page, str(expected_value))


@tag('templatetags')
class CompactFilterTests(TestCase):
    def test_single_line(self):
        content = "  \t Nam  pretium\vturpis  et\tarcu.   \f"
        page = Template("{% load compact from utils %}[{{ my_var|compact }}]").render(Context({'my_var': content}))
        self.assertEqual(page, "[Nam pretium turpis et arcu.]")

    def test_multiple_lines(self):
        content = """
            Maecenas tempus, \t
            tellus  eget\vcondimentum  rhoncus, \f
            sem quam\rsemper libero,  \r
            sit amet  adipiscing   sem\n\n\nneque sed\xA0ipsum.
        """
        page = Template("{% load compact from utils %}[{{ my_var|compact }}]").render(Context({'my_var': content}))
        self.assertEqual(
            page,
            "[Maecenas tempus, tellus eget condimentum rhoncus,"
            " sem quam semper libero, sit amet adipiscing sem neque sed ipsum.]"
        )

    def test_autoescape(self):
        content = "\nPraesent <nonummy   mi> \"in\fodio\".\r\n\t"
        template_string = string.Template("""
            {% load compact from utils %}
            {% autoescape $SWITCH %}
                [{% filter compact %}$CONTENT{% endfilter %}]
                [{% filter compact %}{{ my_var }}{% endfilter %}]/[{{ my_var|compact }}]/
            {% endautoescape %}
        """)
        for switch in ('on', 'off'):
            with self.subTest(autoescape=switch):
                template = Template(template_string.substitute(SWITCH=switch, CONTENT=content))
                page = template.render(Context({'my_var': content}))
                self.assertEqual(
                    page.replace(" "*16, "").strip(),
                    "[Praesent <nonummy mi> \"in odio\".]\n"
                    + (escape if switch == 'on' else lambda x: x)("[Praesent <nonummy mi> \"in odio\".]/") * 2
                )


@tag('templatetags')
class SplitFilterTests(TestCase):
    dummy_object = object()
    test_data = [
        ("", [""]),
        ("xyzq", ["xyzq"]),
        ("1,2,3", ["1", "2", "3"]),
        ("a,b,", ["a", "b", ""]),
        ("a,,c", ["a", "", "c"]),
        (",,,,", ["", "", "", "", ""]),
        ("<a>,<b>,</c>", ["<a>", "<b>", "</c>"]),
        (":'xs',:-&", [":'xs'", ":-&"]),
        (123, [123]),
        (False, [False]),
        (None, [None]),
        (dummy_object, [dummy_object]),
    ]

    def test_var_input(self, autoescape=True):
        # Values of type 'str' are expected to be split into a list of strings,
        # and HTML-encoded on output if autoescape is "on" (output as-is otherwise).
        # Values of other types are expected to be wrapped in a list as-is.
        template_string = string.Template("""
            {% load split from utils %}
            {% autoescape $SWITCH %}
                {% for x in my_var|split:',' %}#{{ x }}#{% endfor %}
            {% endautoescape %}
        """)
        for content, expected_value in self.test_data:
            with self.subTest(value=content):
                template = Template(template_string.substitute(SWITCH='on' if autoescape else 'off'))
                page = template.render(Context({'my_var': content}))
                self.assertEqual(
                    page.strip(),
                    "".join("#{}#".format(escape(part) if autoescape else part) for part in expected_value)
                )

    def test_direct_input(self, autoescape=True):
        # Values of type 'SafeData' are expected to be split into a list of strings,
        # and output as-is.
        template_string = string.Template("""
            {% load split from utils %}
            {% autoescape $SWITCH %}
                {% for x in "$CONTENT"|split:',' %}#{{ x }}#{% endfor %}
            {% endautoescape %}
        """)
        for content, expected_value in self.test_data:
            with self.subTest(value=content):
                template = Template(template_string.substitute(SWITCH='on' if autoescape else 'off', CONTENT=content))
                page = template.render(Context())
                self.assertEqual(page.strip(), "".join("#{}#".format(part) for part in expected_value))

    def test_nonautoescaped_input(self):
        self.test_var_input(autoescape=False)
        self.test_direct_input(autoescape=False)


@tag('templatetags')
class MultFilterTests(TestCase):
    dummy_object = object()
    test_data = [
        ("", {3: "", -3: "", '3': "", '007': "", '-3': "", '': "", '0.03': '', object(): ''}),
        ("xYz", {3: "xYz"*3, -3: "", '3': "xYz"*3, '007': "xYz"*7, '-3': "", '': "", '0.03': '', object(): ''}),
        (123, {3: 369, -3: -369, '3': 369, '007': 861, '-3': -369, '': "", '0.03': '', object(): ''}),
        (False, {3: 0, -3: 0, '3': 0, '007': 0, '-3': 0, '': "", '0.03': '', object(): ''}),
        (None, {3: "", -3: "", '3': "", '007': "", '-3': "", '': "", '0.03': '', object(): ''}),
        (dummy_object, {3: "", -3: "", '3': "", '007': "", '-3': "", '': "", '0.03': '', object(): ''}),
    ]

    def test_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load mult from utils %}{{ 'content'|mult }}")
        self.assertEqual("mult requires 2 arguments, 1 provided", str(cm.exception))

    def test_safe_values(self):
        template_string = string.Template("{% load mult from utils %}{{ $CONTENT|mult:by }}")
        for value, tests in self.test_data:
            for multiplier, outcome in tests.items():
                with self.subTest(value=value, by=multiplier):
                    template = Template(template_string.substitute(
                        CONTENT='"{}"'.format(value) if isinstance(value, str)
                                else 'my_var' if value is self.dummy_object else value
                    ))
                    page = template.render(Context({'my_var': self.dummy_object, 'by': multiplier}))
                    self.assertEqual(page, str(outcome))

    def test_unsafe_values(self):
        template_string = string.Template(
            "{% load mult from utils %}{% autoescape $SWITCH %}{{ my_var|mult:by }}{% endautoescape %}")
        test_data = [
            ("i<j>&k", {2: "i<j>&k"*2, -2: "", '003': "i<j>&k"*3, '0.03': ""}),
        ]
        for value, tests in test_data:
            for multiplier, outcome in tests.items():
                for switch in ('on', 'off'):
                    with self.subTest(value=value, by=multiplier, autoescape=switch):
                        template = Template(template_string.substitute(SWITCH=switch))
                        page = template.render(Context({'my_var': value, 'by': multiplier}))
                        self.assertEqual(page, escape(outcome) if switch == 'on' else outcome)
