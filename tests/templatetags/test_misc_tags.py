import string
import sys
import unittest
from collections import namedtuple
from typing import Any

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.handlers.wsgi import WSGIRequest
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory, TestCase, tag
from django.utils import translation
from django.utils.functional import SimpleLazyObject
from django.utils.html import escape

from factory import Faker


@tag('templatetags')
class RandomIdentifierTagTests(TestCase):
    template_string = string.Template(
        "{% load random_identifier from utils %}"
        "{% random_identifier $LENGTH %}"
    )
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
                self.assertEqual(page, "")

    def test_valid_object(self):
        Cls = namedtuple('ObjectWithFields', 'pk, name, date_joined, date_deleted')
        obj = Cls(pk=1023, name="John", date_joined="2011-02-03", date_deleted="2018-07-06")
        with self.subTest(obj=obj):
            page = Template(self.template_string).render(Context({'my_obj': obj}))
            self.assertEqual(
                page,
                "d64d289bce1a4d5a355bf948a58af770842a008d74bd375f57d182375838994c"
            )

        faker = Faker._get_faker()
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
        page = Template(
            "{% load list from utils %}"
            "{% list 'aa' +2 'bb' -2 'cc' %}"
        ).render(Context())
        self.assertHTMLEqual(page, "[&#39;aa&#39;, 2, &#39;bb&#39;, -2, &#39;cc&#39;]")

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
        page = Template(
            "{% load dict from utils %}"
            "{% dict aa=True bb=False cc=None %}"
        ).render(Context())
        self.assertHTMLEqual(page, "{&#39;aa&#39;: True, &#39;bb&#39;: False, &#39;cc&#39;: None}")

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
class DictInsertTagTests(TestCase):
    def test_missing_source(self):
        # A source dictionary variable not found in context is expected to
        # result in an exception.
        template = Template("{% load dict_insert from utils %}{% dict_insert D 'a' 'AA' %}")
        with self.assertRaises(TypeError):
            template.render(Context())

    def test_output(self):
        # An output variable is expected to not be used, even if provided,
        # and the change performed on the original dictionary.
        template = Template("""
            {% load dict_insert from utils %}
            {% dict_insert D "a" "AA" as D2 %}
            {% dict_insert D "c" "CC" as D3 %}
            {{ D2 }} /
            {{ D3 }} /
            {{ D }}  /
        """)
        page = template.render(Context({'D': {'b': "BB"}}))
        self.assertHTMLEqual(page, "/ / {'b': 'BB', 'a': 'AA', 'c': 'CC'} /")

    def test_single_insert_result(self):
        template = Template("""
            {% load dict_insert from utils %}
            {{ D }}
            {% dict_insert D "a" "AA" %}
            {{ D }}
        """)

        # A single key is expected to be added to the empty dictionary with the
        # specified value.
        page = template.render(Context({'D': {}}))
        self.assertHTMLEqual(page, "{} {'a': 'AA'}")
        # A single key is expected to be inserted into the end of the non-empty
        # dictionary (since Python 3.6), with the specified value.
        page = template.render(Context({'D': {'b': "BB"}}))
        self.assertHTMLEqual(page, "{'b': 'BB'} {'b': 'BB', 'a': 'AA'}")
        # A value for a key that is already present in the non-empty dictionary
        # is expected to overwrite the existing value.
        page = template.render(Context({'D': {'a': "CC"}}))
        self.assertHTMLEqual(page, "{'a': 'CC'} {'a': 'AA'}")

    def test_multiple_insert_result(self):
        template = Template("""
            {% load dict_insert from utils %}
            {{ D }}
            {% dict_insert D a "AA" %}
            {% dict_insert D b 22 %}
            {% dict_insert D c CC %}
            {{ D }}
        """)

        # When keys and values are specified as variables and not found in the
        # context, they are expected to be treated as empty strings. This also
        # means that later values are expected to overwrite previous values.
        page = template.render(Context({'D': {}}))
        self.assertHTMLEqual(page, "{} {'': ''}")
        # A key variable found in context is expected to be added to the empty
        # dictionary, with the rest of the keys behaving as previously.
        page = template.render(Context({'D': {}, 'a': "xx"}))
        self.assertHTMLEqual(page, "{} {'xx': 'AA', '': ''}")
        # Key variables found in context are expected to be added to the empty
        # dictionary in the order and with the values specified via the repeat
        # usage of the template tag.
        page = template.render(Context({'D': {}, 'b': "yy", 'a': "xx"}))
        self.assertHTMLEqual(page, "{} {'xx': 'AA', 'yy': 22, '': ''}")
        # A key variable missing in context is expected to be treated as empty
        # string and not affect the other keys of the dictionary.
        page = template.render(Context({'D': {}, 'c': "yy", 'a': "xx"}))
        self.assertHTMLEqual(page, "{} {'xx': 'AA', '': 22, 'yy': ''}")
        # All key and value variables are expected to be substituted for their
        # actual values in the resulting dictionary, after repeat usage of the
        # template tag.
        page = template.render(Context({
            'D': {},
            'c': "zz", 'CC': "ZZ", 'b': "yy", 'a': "xx", 'AA': "XX",
        }))
        self.assertHTMLEqual(page, "{} {'xx': 'AA', 'yy': 22, 'zz': 'ZZ'}")
        # Later values (according to usage of the tag) for key variables which
        # happen to have the same actual value are expected to overwrite the
        # earlier values in the resulting dictionary.
        page = template.render(Context({
            'D': {},
            'c': "xx", 'CC': 33, 'b': "yy", 'a': "xx",
        }))
        self.assertHTMLEqual(page, "{} {'xx': 33, 'yy': 22}")

    def test_parameter_filters(self):
        # The user of the template tag is expected to be able to apply filters
        # to both the inserted key and the inserted value.
        template = Template("""
            {% load dict_insert from utils %}
            {% dict_insert D e|lower|slice:":2" EE|add:5 %}
            {{ D }}
        """)
        page = template.render(Context({'D': {}, 'e': "XyZ", 'EE': 28}))
        self.assertHTMLEqual(page, "{'xy': 33}")


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
        template = Template("{% load compact from utils %}[{{ my_var|compact }}]")
        page = template.render(Context({'my_var': content}))
        self.assertEqual(page, "[Nam pretium turpis et arcu.]")

    def test_multiple_lines(self):
        content = """
            Maecenas tempus, \t
            tellus  eget\vcondimentum  rhoncus, \f
            sem quam\rsemper libero,  \r
            sit amet  adipiscing   sem\n\n\nneque sed\xA0ipsum.
        """
        template = Template("{% load compact from utils %}[{{ my_var|compact }}]")
        page = template.render(Context({'my_var': content}))
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
                encoding_func = escape if switch == 'on' else lambda x: x
                self.assertEqual(
                    page.replace(" "*16, "").strip(),
                    "[Praesent <nonummy mi> \"in odio\".]\n"
                    + encoding_func("[Praesent <nonummy mi> \"in odio\".]/") * 2
                )


@tag('templatetags')
class SplitFilterTests(TestCase):
    dummy_object = object()
    test_data: list[tuple[Any, dict[str | None, list]]] = [
        ("", {',': [""], None: []}),
        (" \t  ", {',': [" \t  "], None: []}),
        ("xyzqw", {',': ["xyzqw"], None: ["xyzqw"]}),
        ("1,2,3", {',': ["1", "2", "3"], None: ["1,2,3"]}),
        ("a,bb,", {',': ["a", "bb", ""], None: ["a,bb,"]}),
        ("aa,,c", {',': ["aa", "", "c"], None: ["aa,,c"]}),
        (",,,, ", {',': ["", "", "", "", " "], None: [",,,,"]}),
        ("<a>,<b>,</c>", {',': ["<a>", "<b>", "</c>"], None: ["<a>,<b>,</c>"]}),
        ("<a> <b> </c>", {',': ["<a> <b> </c>"], None: ["<a>", "<b>", "</c>"]}),
        (":'xs',:-&,<>", {',': [":'xs'", ":-&", "<>"], None: [":'xs',:-&,<>"], ':': ["", "'xs',", "-&,<>"]}),
        (" i\xA0t\\tq ", {'t': [" i\xA0", "\\", "q "], None: ["i", "t\\tq"], "\\\\": [" i\xA0t", "tq "]}),
        (123, {',': [123], None: [123]}),
        (False, {',': [False], None: [False]}),
        (None, {',': [None], None: [None]}),
        (dummy_object, {',': [dummy_object], ':': [dummy_object]}),
    ]

    def test_var_input(self, autoescape=True, test_data=None):
        # Values of type 'str' are expected to be split into a list of strings,
        # and HTML-encoded on output if autoescape is "on" (output as-is otherwise).
        # Values of other types are expected to be wrapped in a list as-is.
        template_string = string.Template("""
            {% load split from utils %}
            {% autoescape $SWITCH %}
                {% for x in my_var|split$SEP %}#{{ x }}#{% endfor %}
            {% endautoescape %}
        """)
        for content, expected_values in (test_data or self.test_data):
            for sep in expected_values:
                with self.subTest(value=content, separator=sep):
                    template = Template(template_string.substitute(
                        SWITCH='on' if autoescape else 'off',
                        SEP=':"{}"'.format(sep) if sep else ''))
                    page = template.render(Context({'my_var': content}))
                    self.assertEqual(
                        page.strip(),
                        "".join(
                            "#{}#".format(escape(part) if autoescape else part)
                            for part in expected_values[sep]
                        )
                    )

    def test_direct_input(self, autoescape=True, test_data=None):
        # Values of type 'SafeData' are expected to be split into a list of strings,
        # and output as-is.
        template_string = string.Template("""
            {% load split from utils %}
            {% autoescape $SWITCH %}
                {% for x in "$CONTENT"|split$SEP %}#{{ x }}#{% endfor %}
            {% endautoescape %}
        """)
        for content, expected_values in (test_data or self.test_data):
            for sep in expected_values:
                with self.subTest(value=content, separator=sep):
                    template = Template(template_string.substitute(
                        SWITCH='on' if autoescape else 'off',
                        CONTENT=content,
                        SEP=':"{}"'.format(sep) if sep else ''))
                    page = template.render(Context())
                    self.assertEqual(
                        page.strip(),
                        "".join(
                            "#{}#".format(part) for part in expected_values[sep]
                        )
                    )

    def test_nonautoescaped_var_input(self):
        self.test_var_input(autoescape=False)

    def test_nonautoescaped_direct_input(self):
        self.test_direct_input(autoescape=False)

    def test_newline_var_input(self):
        test_data = [
            ("<a>\n\n<b>\n", {
                '>': ["<a", "\n\n<b", "\n"],
                '<a>': ["", "\n\n<b>\n"],
                'NEWLINE': ["<a>", "", "<b>", ""]
            }),
        ]
        self.test_var_input(test_data=test_data, autoescape=True)
        self.test_var_input(test_data=test_data, autoescape=False)

    def do_test_with_chunks(self, *, var, autoescape):
        test_data = (
            "This message;\t<strong>along with the apple</strong>;"
            " is sent on behalf of <span>Adam</span>;"
        )
        expected = {
            # no separator, no chunk length
            '~': [False, [test_data]],
            # separator is tilda, no chunk length
            '~~': [False, [test_data]],
            # no separator, chunk length 14
            '~14': [
                True,
                ["This message;\t", "<strong>along ", "with the apple", "</strong>; is ", "sent on behalf",
                 " of <span>Adam", "</span>;"]],
            # separator is space, chunk length 4
            ' ~4': [
                True,
                ["This", "mess", "age;", "\t<st", "rong", ">alo", "ng", "with", "the", "appl", "e</s", "tron",
                 "g>;", "is", "sent", "on", "beha", "lf", "of", "<spa", "n>Ad", "am</", "span", ">;"]],
            # separator is semicolon, chunk length 9
            ';~9': [
                True,
                ["This mess", "age", "\t<strong>", "along wit", "h the app", "le</stron", "g>", " is sent ",
                 "on behalf", " of <span", ">Adam</sp", "an>", ""]],
            # separator is angle bracket, no chunk length
            '<~': [
                False,
                ["This message;\t", "strong>along with the apple", "/strong>; is sent on behalf of ",
                 "span>Adam", "/span>;"]],
            # separator is angle bracket, chunk length is invalid
            '<~aab': [
                False,
                ["This message;\t", "strong>along with the apple", "/strong>; is sent on behalf of ",
                 "span>Adam", "/span>;"]],
            # separator is angle bracket, chunk length is invalid
            '<~9.3': [
                False,
                ["This message;\t", "strong>along with the apple", "/strong>; is sent on behalf of ",
                 "span>Adam", "/span>;"]],
            # separator is angle bracket, chunk length 17
            '<~-17': [
                True,
                ["This message;\t", "strong>along with", " the apple", "/strong>; is sent", " on behalf of ",
                 "span>Adam", "/span>;"]],
            # separator is tab-tilda-tab, chunk length 42
            '\t~\t~42': [
                True,
                ["This message;\t<strong>along with the apple", "</strong>; is sent on behalf of <span>Adam",
                 "</span>;"]],
            # separator is tilda-tilda, chunk length 99
            '~~~99': [True, [test_data]],
        }

        template_string = string.Template("""
            {% load split from utils %}
            {% autoescape $SWITCH %}
                {% for x in $DATA|split:'$SEP' %}#{{ x }}#{% endfor %}
            {% endautoescape %}
        """)

        for sep in expected:
            with self.subTest(separator=sep):
                template = Template(template_string.substitute(
                    SWITCH='on' if autoescape else 'off',
                    DATA='my_var' if var else '"{}"'.format(test_data),
                    SEP=sep))
                page = template.render(Context({'my_var': test_data}))
                self.assertEqual(
                    page.strip(),
                    "".join(
                        "#{}#".format(
                            escape(part) if autoescape and (var or expected[sep][0]) else part)
                        for part in expected[sep][1]
                    )
                )

    def test_chunking_var_input_autoescaped(self):
        self.do_test_with_chunks(var=True, autoescape=True)

    def test_chunking_var_input_nonautoescaped(self):
        self.do_test_with_chunks(var=True, autoescape=False)

    def test_chunking_direct_input_autoescaped(self):
        self.do_test_with_chunks(var=False, autoescape=True)

    def test_chunking_direct_input_nonautoescaped(self):
        self.do_test_with_chunks(var=False, autoescape=False)


@tag('templatetags')
class MultFilterTests(TestCase):
    dummy_object = object()
    test_data: list[tuple[Any, dict[Any, str | float]]] = [
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
                    page = template.render(
                        Context({
                            'my_var': self.dummy_object, 'by': multiplier,
                        })
                    )
                    self.assertEqual(page, str(outcome))

    def test_unsafe_values(self):
        template_string = string.Template(
            "{% load mult from utils %}"
            "{% autoescape $SWITCH %}{{ my_var|mult:by }}{% endautoescape %}"
        )
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


@tag('templatetags')
class LanguageTagTests(TestCase):
    def test_get_system_language(self):
        page = Template(
            "{% load get_system_language from utils %}"
            "{% get_system_language %}"
        ).render(Context())
        self.assertEqual(page, f"{ settings.LANGUAGE_CODE }")

        page = Template(
            "{% load get_system_language from utils %}"
            "{% get_system_language as LANG %}//[{{ LANG }}]"
        ).render(Context())
        self.assertEqual(page, f"//[{ settings.LANGUAGE_CODE }]")

        page = Template(
            "{% load i18n %}{% load get_system_language from utils %}"
            "{% language 'mn-CN' %}{% get_system_language %}{% endlanguage %}"
        ).render(Context())
        self.assertEqual(page, "mn-cn")

        with translation.override('ga'):
            page = Template(
                "{% load get_system_language from utils %}"
                "{% get_system_language %}"
            ).render(Context())
        self.assertEqual(page, "ga")

    def test_get_user_language(self):
        template_direct_output = Template(
            "{% load get_user_language from utils %}"
            "{% get_user_language %}"
        )
        template_output_via_var = Template(
            "{% load get_user_language from utils %}"
            "{% get_user_language as LANG %}//[{{ LANG }}]"
        )
        template_forced_locale = Template(
            "{% load i18n %}{% load get_user_language from utils %}"
            "{% language 'ga' %}{% get_user_language %}{% endlanguage %}"
        )

        test_data: list[tuple[WSGIRequest | None, str]] = [
            # If the request does not indicate a language preference, the system language
            # is expected to be returned.
            (RequestFactory().get('/'), "fa"),
            # If the request indicates a language variant preference not supported by the
            # system, the base language code is expected to be returned.
            (RequestFactory().get('/', HTTP_ACCEPT_LANGUAGE='mn-ja'), "mn"),
            # When the request indicates several preferred languages, the first supported
            # by the system is expected to be returned.
            (RequestFactory().get('/', HTTP_ACCEPT_LANGUAGE='xx-cn, yy, az'), "az"),
            # If the request indicates only unsupported preferred languages, the system
            # language is expected to be returned.
            (RequestFactory().get('/', HTTP_ACCEPT_LANGUAGE='xyz'), "fa"),
            # When no request is present in the context, the system language is expected
            # to be returned.
            (None, "fa")
        ]

        for request, expected_lang_code in test_data:
            with self.subTest(
                    request={
                        k: v for k, v in request.META.items() if k == 'HTTP_ACCEPT_LANGUAGE'
                    } if request else None
            ):
                with self.settings(LANGUAGE_CODE='fa'):
                    context = Context({'request': request}) if request else Context()
                    self.assertEqual(
                        template_direct_output.render(context),
                        f"{expected_lang_code}"
                    )
                    self.assertEqual(
                        template_output_via_var.render(context),
                        f"//[{expected_lang_code}]"
                    )
                    # The locally activated locale is expected to be ignored in favor of
                    # the base system language, when user does not indicate a language
                    # preference or that preferred language is unsupported.
                    self.assertEqual(
                        template_forced_locale.render(context),
                        f"{expected_lang_code}"
                    )


@tag('templatetags')
class ContentPageLanguageFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.content_page_one = FlatPage(url='/test/cn/one/')
        cls.content_page_two = FlatPage(url='/test/again/cn/two/')

    def test_filter(self):
        template = Template(
            "{% load content_page_language from utils %}"
            "{{ page|content_page_language }}"
        )
        page = template.render(Context({'page': self.content_page_one}))
        self.assertEqual(page, "cn")

        # When language code is not present in the URL of the content page, the
        # result is expected to be an empty string.
        page = template.render(Context({'page': FlatPage(url='/different-block/')}))
        self.assertEqual(page, "")

        # Sanity check.
        with self.assertRaises(AttributeError):
            template.render(Context({'page': None}))
        with self.assertRaises(AttributeError):
            template.render(Context({'page': object()}))

    def test_filter_with_prefix(self):
        template = Template(
            "{% load content_page_language from utils %}"
            "{{ page|content_page_language:'/test/again' }}"
        )
        page = template.render(Context({'page': self.content_page_two}))
        self.assertEqual(page, "cn")
        page = template.render(Context({'page': self.content_page_one}))
        self.assertEqual(page, "cn")

        template = Template(
            "{% load content_page_language from utils %}"
            "{{ page|content_page_language:'/test/again/' }}"
        )
        page = template.render(Context({'page': self.content_page_two}))
        self.assertEqual(page, "cn")
        page = template.render(Context({'page': self.content_page_one}))
        self.assertEqual(page, "cn")

        template = Template(
            "{% load content_page_language from utils %}"
            "{{ page|content_page_language:'/cadabra/' }}"
        )
        page = template.render(Context({'page': self.content_page_two}))
        self.assertEqual(page, "again")
        page = template.render(Context({'page': self.content_page_one}))
        self.assertEqual(page, "cn")

        # Sanity check.
        with self.assertRaises(AttributeError):
            template.render(Context({'page': None}))
        with self.assertRaises(AttributeError):
            template.render(Context({'page': object()}))
