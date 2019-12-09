import string
from collections import namedtuple

from django.template import Context, Template
from django.test import tag

from django_webtest import WebTest
from factory import Faker


@tag('templatetags')
class RandomIdentifierTagTests(WebTest):
    template_string = string.Template("{% load random_identifier from utils %}{% random_identifier $LENGTH %}")
    re_default = r'^[A-Za-z1-9_]{16,48}$'

    def test_no_length(self):
        template = Template(self.template_string.substitute(LENGTH=""))
        page = template.render(Context({}))
        self.assertRegex(page, self.re_default)

    def test_invalid_length(self):
        for length in ("aaabbbcc", -6, -12.34, "qwerty1sadf", 0, "view.non_existent_attr"):
            with self.subTest(id_len=length):
                template = Template(self.template_string.substitute(LENGTH=length))
                page = template.render(Context({}))
                self.assertRegex(page, self.re_default)

    def test_valid_length(self):
        for length in range(1, 200):
            with self.subTest(id_len=length):
                template = Template(self.template_string.substitute(LENGTH=length))
                page = template.render(Context({}))
                self.assertRegex(page, r'^[A-Za-z1-9_]{%d}$' % length)


@tag('templatetags')
class PublicIdFilterTests(WebTest):
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

        first_obj = Cls(
            pk=Faker('pyint').generate({}),
            name=Faker('first_name').generate({}),
            date_joined=Faker('past_date').generate({}),
            date_deleted=Faker('future_date').generate({}))
        hash_of_obj = ""
        object_list = [first_obj]
        for i in range(15):
            obj = Cls(
                pk=first_obj.pk,
                date_joined=first_obj.date_joined,
                name=Faker('first_name').generate({}),
                date_deleted=Faker('future_date').generate({}))
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
class CompactFilterTests(WebTest):
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
