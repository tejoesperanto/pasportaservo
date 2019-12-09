from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory, tag

from django_webtest import WebTest


@tag('templatetags')
class NextTagTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.request_factory = RequestFactory()
        cls.redirect_field_name = settings.REDIRECT_FIELD_NAME

    def test_incorrect_syntax(self):
        # Missing arguments are expected to raise a TemplateSyntaxError or TypeError.
        for variant in ["{% next %}", "{% next as url %}"]:
            with self.subTest(faulty_tag=variant):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template("{% load next from utils %}" + variant)
                self.assertIn("did not receive value(s) for the argument(s): 'proceed_to'", str(cm.exception))

        for variant in ["{% next url_only=True %}", "{% next default=X %}", "{% next url_only=True as url %}"]:
            with self.subTest(faulty_tag=variant):
                with self.assertRaises(TypeError) as cm:
                    Template("{% load next from utils %}" + variant).render(Context({}))
                self.assertIn("missing 1 required positional argument: 'proceed_to'", str(cm.exception))

    def test_provided_link(self):
        expected_value = "{}=%2Fxx%2Fyy%2Fzz%23qq-32".format(self.redirect_field_name)

        # A directly provided URL is expected to be used as-is.
        template = Template("{% load next from utils %}{% next '/xx/yy/zz#qq-32' %}")
        page = template.render(Context({}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-32' %}")
        page = template.render(Context({}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-' 32 %}")
        page = template.render(Context({}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-' obj_pk %}")
        page = template.render(Context({'obj_pk': 32}))
        self.assertEqual(page, expected_value)

    def test_thispage_link(self):
        # The token 'this page' is supposed to use the current request's URL, but if
        # the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next 'this page' %}")
        page = template.render(Context({}))
        self.assertEqual(page, "")

        request = self.request_factory.get('/trololo/lolo/lo-lo-lo?LoLoLo')
        expected_value = "{}=%2Ftrololo%2Flolo%2Flo-lo-lo%3FLoLoLo".format(self.redirect_field_name)

        # The token 'this page' is expected to result in the current request's URL.
        template = Template("{% load next from utils %}{% next 'this page' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next 'this page' '#x' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "{}%23x".format(expected_value))

        template = Template("{% load next from utils %}{% next 'this page' '#x' 150 %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "{}%23x150".format(expected_value))

    def test_thispage_shortcut_link(self):
        # When an anchor is used, the 'this page' token (using the current request's URL) is assumed, but if
        # the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next '#y2' %}")
        page = template.render(Context({}))
        self.assertEqual(page, "")

        request = self.request_factory.get('/tra/LA/la/la-la#aaaa')
        expected_value = "{}=%2Ftra%2FLA%2Fla%2Fla-la%23y2".format(self.redirect_field_name)

        # When an anchor is used, the 'this page' token is assumed. Therefore the current request's URL is expected.
        template = Template("{% load next from utils %}{% next '#y2' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '#y' '2' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

    def test_nextpage_link(self):
        # The token 'next page' is supposed to use the value of the request parameter, but if
        # the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        page = template.render(Context({}))
        self.assertEqual(page, "")
        # The token 'next page' is supposed to use the value of the request parameter, but if
        # the paramater is not present in the request, an empty result is expected.
        page = template.render(Context({'request': self.request_factory.get('/ensaluti/')}))
        self.assertEqual(page, "")

        request = self.request_factory.get(
            '/ensaluti/?{}=/profilo/eduard/khil/1976%23familio'.format(self.redirect_field_name))
        expected_value = "{}=%2Fprofilo%2Feduard%2Fkhil%2F1976%23familio".format(self.redirect_field_name)

        # The token 'next page' is expected to result in the value of the corresponding request parameter.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next 'next page' '#2009' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "{}%232009".format(expected_value))

        template = Template("{% load next from utils %}{% next 'next page' '#2009' '=3M' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "{}%232009%3D3M".format(expected_value))

    def test_insecure_nextpage_link(self):
        # The token 'next page' is supposed to use the value of the request parameter. Whenever the value supplied
        # is not secure (points to an unexpected URL or an external domain), an empty result is expected.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        for url, secure in (('//example.com/landing', False),
                            ('http://example.net/landing', False),
                            ('https://example.org/landing', True),
                            ('http://testserver/malicious/P-page', True)):
            with self.subTest(redirect=url):
                request = self.request_factory.get(
                    '/folio/?{}={}'.format(self.redirect_field_name, url), secure=secure)
                page = template.render(Context({'request': request}))
                self.assertEqual(page, "")

    def test_urlonly_value(self):
        # The 'url_only' flag together with a directly provided URL is expected to result in this URL.
        template = Template("{% load next from utils %}[{% next '/abc/def/ghij?klmn=op' url_only=True %}]")
        page = template.render(Context({}))
        self.assertEqual(page, "[/abc/def/ghij?klmn=op]")

        # The 'url_only' flag together with a directly provided URL is expected to result in this URL.
        template = Template(
            "{% load next from utils %}"
            "[{% next '/<object>/' url_only=True as next_url %}][{{ next_url }}]")
        page = template.render(Context({}))
        self.assertEqual(page, "[][/&lt;object&gt;/]")

        request = self.request_factory.get('/q/rs/tuv?w=W&{}=/xyz'.format(self.redirect_field_name))

        # The 'url_only' flag together with 'this page' token
        # is expected to result in the current request's URL.
        template = Template("{% load next from utils %}[{% next 'this page' url_only=True %}]")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "[/q/rs/tuv?w=W&amp;{}=/xyz]".format(self.redirect_field_name))

        # The 'url_only' flag together with 'next page' token
        # is expected to result in the value of the corresponding request parameter.
        template = Template("{% load next from utils %}[{% next 'next page' url_only=True %}]")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "[/xyz]")

    def test_default_value(self):
        expected_value = "{}=Finally%20Returning%20Back%20Home".format(self.redirect_field_name)

        # A value provided as 'default' is expected to be used when the first argument evaluates to empty string.
        template = Template("{% load next from utils %}{% next '' default='Finally Returning Back Home' %}")
        page = template.render(Context({}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next next_url default=builtin_url %}")
        page = template.render(Context({}))
        self.assertEqual(page, "")
        page = template.render(Context({'builtin_url': "Finally Returning Back Home"}))
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}[{% next next_url url_only=True default=builtin_url %}]")
        page = template.render(Context({'next_url': None, 'builtin_url': "Finally Returning Back Home"}))
        self.assertEqual(page, "[Finally Returning Back Home]")
        page = template.render(Context({'next_url': False, 'builtin_url': None}))
        self.assertEqual(page, "[]")

        template = Template("{% load next from utils %}{% next 'next page' default=builtin_url %}")
        request = self.request_factory.get('/IAm/Very-Glad/?nextt=')
        page = template.render(Context({'request': request, 'builtin_url': "Finally Returning Back Home"}))
        self.assertEqual(page, expected_value)
        page = template.render(Context({'request': request, 'builtin_url': None}))
        self.assertEqual(page, "")
