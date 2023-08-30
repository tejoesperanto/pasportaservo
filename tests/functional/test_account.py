import re

from django.core import mail
from django.test import override_settings, tag
from django.urls import reverse, reverse_lazy

from django_webtest import WebTest

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


@tag('functional', 'views', 'views-session', 'views-login')
class InactiveUserLoginTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('login')
        cls.user = UserFactory(profile=None, is_active=False)

    def login_attempt_tests(self, lang):
        # A user who supplied the correct credentials but whose account was
        # deactivated, is expected to be denied login.
        # A warning is expected to be recorded in the authentication log,
        # containing the restore_request_id; the same id is expected in the
        # email sent to the administrators once the user clicks the link to
        # notify them about the user's desire to reactivate the account.

        page = self.app.get(self.url, status=200)
        page.form['username'] = self.user.username
        page.form['password'] = "adm1n"
        with self.assertLogs('PasportaServo.auth', level='WARNING') as log:
            result_page = page.form.submit()
        # A status code of 200 means the user is returned to the login page
        # with an error; otherwise the status code would have been 302.
        self.assertEqual(result_page.status_code, 200)
        self.assertLength(log.records, 1)
        m = re.search(r'\[([A-F0-9-]+)\]', log.output[0])
        self.assertIsNotNone(m, msg="restore_request_id was not logged.")
        notification_id = m.group(1)
        mail.outbox = []
        # Simulate a click on the "request reactivation" link.
        status_page = result_page.click(href=lambda href: href == reverse('login_restore'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            {
                'en': "Note to admin: User requests to reactivate their account",
                'eo': "Sciigo al admino: Uzanto petas reaktivigi sian PS-konton",
            }[lang],
            mail.outbox[0].subject
        )
        self.assertIn(notification_id, mail.outbox[0].subject)
        self.assertEqual(status_page.status_code, 200)
        self.assertContains(
            status_page,
            {
                'en': "An administrator will contact you soon.",
                'eo': "Administranto baldaŭ kontaktiĝos kun vi.",
            }[lang]
        )

    def test_login(self):
        for lang in ['en', 'eo']:
            with override_settings(LANGUAGE_CODE=lang):
                with self.subTest(lang=lang):
                    self.login_attempt_tests(lang)
