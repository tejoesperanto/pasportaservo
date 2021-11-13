from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory, TestCase, tag

from core.templatetags.utils import next_link


@tag('templatetags')
class NextTagTests(TestCase):
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
                    Template("{% load next from utils %}" + variant).render(Context())
                self.assertIn("missing 1 required positional argument: 'proceed_to'", str(cm.exception))

    def test_provided_link(self):
        expected_value = f"{self.redirect_field_name}=%2Fxx%2Fyy%2Fzz%23qq-32"

        # A directly provided URL is expected to be used as-is.
        template = Template("{% load next from utils %}{% next '/xx/yy/zz#qq-32' %}")
        page = template.render(Context())
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-32' %}")
        page = template.render(Context())
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-' 32 %}")
        page = template.render(Context())
        self.assertEqual(page, expected_value)

        template = Template("{% load next from utils %}{% next '/xx/yy/zz' '#qq-' obj_pk %}")
        page = template.render(Context({'obj_pk': 32}))
        self.assertEqual(page, expected_value)

    def test_thispage_link(self):
        # The token 'this page' is supposed to use the current request's URL, but if
        # the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next 'this page' %}")
        page = template.render(Context())
        self.assertEqual(page, "")

        request = self.request_factory.get('/trololo/lolo/lo-lo-lo?LoLoLo')
        expected_value = f"{self.redirect_field_name}=%2Ftrololo%2Flolo%2Flo-lo-lo%3FLoLoLo"

        # The token 'this page' is expected to result in the current request's URL.
        template = Template("{% load next from utils %}{% next 'this page' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)
        value = next_link(request, 'this page')
        self.assertEqual(value, expected_value)

        template = Template("{% load next from utils %}{% next 'this page' '#x' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, f"{expected_value}%23x")
        value = next_link(request, 'this page', "#x")
        self.assertEqual(value, f"{expected_value}%23x")

        template = Template("{% load next from utils %}{% next 'this page' '#x' 150 %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, f"{expected_value}%23x150")
        value = next_link(request, 'this page', "#x", 150)
        self.assertEqual(value, f"{expected_value}%23x150")

    def test_thispage_shortcut_link(self):
        # When an anchor is used, the 'this page' token (using the current request's URL) is assumed,
        # but if the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next '#y2' %}")
        page = template.render(Context())
        self.assertEqual(page, "")

        request = self.request_factory.get('/tra/LA/la/la-la#aaaa')
        expected_value = f"{self.redirect_field_name}=%2Ftra%2FLA%2Fla%2Fla-la%23y2"

        # When an anchor is used, the 'this page' token is assumed.
        # Therefore the current request's URL is expected.
        template = Template("{% load next from utils %}{% next '#y2' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)
        value = next_link(request, "#y2")
        self.assertEqual(value, expected_value)

        template = Template("{% load next from utils %}{% next '#y' '2' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)
        value = next_link(request, "#y", 2)
        self.assertEqual(value, expected_value)

    def test_nextpage_link(self):
        # The token 'next page' is supposed to use the value of the request parameter, but if
        # the request object is missing from context, an empty result is expected.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        page = template.render(Context())
        self.assertEqual(page, "")
        # The token 'next page' is supposed to use the value of the request parameter, but if
        # the parameter is not present in the request, an empty result is expected.
        page = template.render(Context({'request': self.request_factory.get('/ensaluti/')}))
        self.assertEqual(page, "")

        request = self.request_factory.get(
            f'/ensaluti/?{self.redirect_field_name}=/profilo/eduard/khil/1976%23familio')
        expected_value = f"{self.redirect_field_name}=%2Fprofilo%2Feduard%2Fkhil%2F1976%23familio"

        # The token 'next page' is expected to result in the value of the corresponding request parameter.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)
        value = next_link(request, 'next page')
        self.assertEqual(value, expected_value)

        template = Template("{% load next from utils %}{% next 'next page' '#2009' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, f"{expected_value}%232009")
        value = next_link(request, 'next page', "#2009")
        self.assertEqual(value, f"{expected_value}%232009")

        template = Template("{% load next from utils %}{% next 'next page' '#2009' '=3M' %}")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, f"{expected_value}%232009%3D3M")
        value = next_link(request, 'next page', "#2009", "=3M")
        self.assertEqual(value, f"{expected_value}%232009%3D3M")

    def test_insecure_nextpage_link(self):
        # The token 'next page' is supposed to use the value of the request parameter. Whenever the
        # value supplied is not secure (points to an unexpected URL or an external domain), an empty
        # result is expected.
        template = Template("{% load next from utils %}{% next 'next page' %}")
        for url, secure in [('//example.com/landing', False),
                            ('http://example.net/landing', False),
                            ('https://example.org/landing', True),
                            ('http://testserver/malicious/P-page', True)]:
            with self.subTest(redirect=url):
                request = self.request_factory.get(
                    f'/folio/?{self.redirect_field_name}={url}', secure=secure)
                page = template.render(Context({'request': request}))
                self.assertEqual(page, "")

    def test_urlonly_value(self):
        # The 'url_only' flag together with a directly provided URL is expected to result in this URL.
        template = Template(
            "{% load next from utils %}"
            "[{% next '/abc/def/ghij?klmn=op' url_only=True %}]")
        page = template.render(Context())
        self.assertEqual(page, "[/abc/def/ghij?klmn=op]")

        # The 'url_only' flag together with a directly provided URL is expected to result in this URL.
        template = Template(
            "{% load next from utils %}"
            "[{% next '/<object>/' url_only=True as next_url %}][{{ next_url }}]")
        page = template.render(Context())
        self.assertEqual(page, "[][/&lt;object&gt;/]")

        request = self.request_factory.get(f'/q/rs/tuv?w=W&{self.redirect_field_name}=/xyz')

        # The 'url_only' flag together with 'this page' token
        # is expected to result in the current request's URL.
        template = Template("{% load next from utils %}[{% next 'this page' url_only=True %}]")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, f"[/q/rs/tuv?w=W&amp;{self.redirect_field_name}=/xyz]")
        value = next_link(request, 'this page', url_only=True)
        self.assertEqual(value, f"/q/rs/tuv?w=W&{self.redirect_field_name}=/xyz")

        # The 'url_only' flag together with 'next page' token
        # is expected to result in the value of the corresponding request parameter.
        template = Template("{% load next from utils %}[{% next 'next page' url_only=True %}]")
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "[/xyz]")
        value = next_link(request, 'next page', url_only=True)
        self.assertEqual(value, "/xyz")

    def test_default_value(self):
        expected_value = f"{self.redirect_field_name}=Finally%20Returning%20Back%20Home"

        # A value provided as 'default' is expected to be used
        # when the first argument evaluates to empty string.
        template = Template(
            "{% load next from utils %}"
            "{% next '' default='Finally Returning Back Home' %}")
        page = template.render(Context())
        self.assertEqual(page, expected_value)

        template = Template(
            "{% load next from utils %}"
            "{% next next_url default=builtin_url %}")
        page = template.render(Context())
        self.assertEqual(page, "")
        page = template.render(Context({'builtin_url': "Finally Returning Back Home"}))
        self.assertEqual(page, expected_value)

        template = Template(
            "{% load next from utils %}"
            "[{% next next_url url_only=True default=builtin_url %}]")
        page = template.render(
            Context({'next_url': None, 'builtin_url': "Finally Returning Back Home"})
        )
        self.assertEqual(page, "[Finally Returning Back Home]")
        page = template.render(Context({'next_url': False, 'builtin_url': None}))
        self.assertEqual(page, "[]")

        template = Template(
            "{% load next from utils %}"
            "{% next 'next page' default=builtin_url %}")
        request = self.request_factory.get('/IAm/Very-Glad/?nextt=')
        page = template.render(
            Context({'request': request, 'builtin_url': "Finally Returning Back Home"})
        )
        self.assertEqual(page, expected_value)
        value = next_link(request, 'next page', default="Finally Returning Back Home")
        self.assertEqual(value, expected_value)
        page = template.render(Context({'request': request, 'builtin_url': None}))
        self.assertEqual(page, "")
        value = next_link(request, 'next page', default=None)
        self.assertEqual(value, "")


@tag('templatetags')
class PreviousTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.request_factory = RequestFactory()

    def test_prevpage_link(self):
        template = Template("{% load previous from utils %}{% previous %}")
        # Missing request in context is expected to produce an empty result.
        page = template.render(Context())
        self.assertEqual(page, "")
        # Request with no referer header is expected to produce an empty result.
        request = self.request_factory.get('/festival')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "")
        # Request including a URL path referer header is expected to produce the value of the header.
        request = self.request_factory.get('/festival', HTTP_REFERER='/1965/songs')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "/1965/songs")
        # Request including a full referer header is expected to produce the URL path of the header.
        request = self.request_factory.get('/festival', HTTP_REFERER='http://testserver/1968/award')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, "/1968/award")

    def test_insecure_prevpage_link(self):
        # Requests whose referer header is not secure (points to an unexpected URL or an external domain),
        # are expected to produce an empty result.
        template = Template("{% load previous from utils %}{% previous %}")
        for url, secure in [('//example.com/landing', False),
                            ('http://example.net/landing', False),
                            ('https://example.org/landing', True),
                            ('http://testserver/malicious/P-page', True)]:
            with self.subTest(referer=url):
                request = self.request_factory.get('/folio/2021', secure=secure, HTTP_REFERER=url)
                page = template.render(Context({'request': request}))
                self.assertEqual(page, "")

    def test_default_value(self):
        # A value provided as 'default' is expected to be used when
        # the request's referer header is either missing, empty, or insecure.
        template = Template(
            "{% load previous from utils %}"
            "{% previous default='/Finally_Returning/Back=Home' %}")
        expected_value = "/Finally_Returning/Back=Home"

        page = template.render(Context())
        self.assertEqual(page, expected_value)

        request = self.request_factory.get('/IAm/Very-Glad/')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

        request = self.request_factory.get('/IAm/Very-Glad', HTTP_REFERER='')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)

        request = self.request_factory.get(
            f'/IAm/Very-Glad?{settings.REDIRECT_FIELD_NAME}=/1976', HTTP_REFERER='//trolo.lo')
        page = template.render(Context({'request': request}))
        self.assertEqual(page, expected_value)
