from django.contrib.sites.models import Site
from django.template import Context, Template
from django.test import RequestFactory, TestCase, tag


@tag('templatetags')
class DomainTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.request_factory = RequestFactory()
        cls.template_sans_url = Template("{% load domain %}{% domain %}")
        cls.template_with_url = Template("{% load domain %}{% domain '/418?I=am&Teapot' %}")

    def setUp(self):
        first_site = Site.objects.get(id=1)
        first_site.name, first_site.domain = 'MyTestServer', 'mytestsrv'
        # We cannot use QS.update() because it does not trigger the `save` signal
        # (which clears the site cache; see django.contrib.sites.models.SiteManager).
        first_site.save()
        Site.objects.create(name='TestPS', domain='test.pasportaservo.org.mondo')

    def test_through_request(self):
        # A typical web page template has a 'request' context variable and the values
        # of scheme+host are expected to be taken from the Request.
        request = self.request_factory.get('/404')
        page = self.template_sans_url.render(Context({'request': request}))
        self.assertEqual(page, "http://mytestsrv")
        page = self.template_with_url.render(Context({'request': request}))
        self.assertEqual(page, "http://mytestsrv/418?I=am&amp;Teapot")

        request = self.request_factory.get('/404', secure=True)
        page = self.template_sans_url.render(Context({'request': request}))
        self.assertEqual(page, "https://mytestsrv")
        page = self.template_with_url.render(Context({'request': request}))
        self.assertEqual(page, "https://mytestsrv/418?I=am&amp;Teapot")

    def test_through_django_email(self):
        # A Django email template has 'protocol' & 'domain' context variables and the
        # values of scheme+host are expected to be matching these variables.
        page = self.template_sans_url.render(Context({'protocol': "xkcd", 'domain': "initialism"}))
        self.assertEqual(page, "xkcd://initialism")
        page = self.template_with_url.render(Context({'protocol': "xkcd", 'domain': "initialism"}))
        self.assertEqual(page, "xkcd://initialism/418?I=am&amp;Teapot")

    def test_through_postman_email(self):
        # A Postman email template has a 'site' context variable and the value of the
        # host is expected to be extracted from the Site, while the scheme is expected
        # to vary according to the hostname.
        page = self.template_sans_url.render(Context({'site': Site.objects.get(name='MyTestServer')}))
        self.assertEqual(page, "http://mytestsrv")
        page = self.template_with_url.render(Context({'site': Site.objects.get(name='MyTestServer')}))
        self.assertEqual(page, "http://mytestsrv/418?I=am&amp;Teapot")

        page = self.template_sans_url.render(Context({'site': Site.objects.get(name='TestPS')}))
        self.assertEqual(page, "https://test.pasportaservo.org.mondo")
        page = self.template_with_url.render(Context({'site': Site.objects.get(name='TestPS')}))
        self.assertEqual(page, "https://test.pasportaservo.org.mondo/418?I=am&amp;Teapot")

    def test_fallback(self):
        # When no suitable context variables are available, the result is expected to
        # be a fallback, dependent on the DEBUG status (True = dev/test environment,
        # False = acc/prod env).
        with self.settings(ALLOWED_HOSTS=['mytestsrv', 'testserver']):
            page = self.template_sans_url.render(Context())
            self.assertEqual(page, "https://mytestsrv")
            page = self.template_with_url.render(Context())
            self.assertEqual(page, "https://mytestsrv/418?I=am&amp;Teapot")

        with self.settings(DEBUG=True):
            page = self.template_sans_url.render(Context())
            self.assertEqual(page, "http://localhost:8000")
            page = self.template_with_url.render(Context())
            self.assertEqual(page, "http://localhost:8000/418?I=am&amp;Teapot")
