from django_webtest import WebTest


class UrlTests(WebTest):

    def test_home(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_profile(self):
        response = self.app.get('/profilo/')
        self.assertEqual(response.location, '/ensaluti/?ps_m=/profilo/')
        self.assertEqual(response.status_code, 302)
