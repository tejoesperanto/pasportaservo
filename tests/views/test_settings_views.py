from typing import cast
from urllib.parse import urlencode

from django.conf import settings
from django.test import override_settings, tag
from django.urls import reverse_lazy

from pyquery import PyQuery

from ..factories import UserFactory
from .pages import AccountSettingsPage
from .testcasebase import BasicViewTests


@tag('views', 'views-account', 'views-settings')
class AccountSettingsViewTests(BasicViewTests):
    view_page = AccountSettingsPage

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user_with_profile = cls.user
        cls.user = cls.users['basic']
        cls.user.username = f'{cls.user.username}<hr>'
        cls.user.save()
        del cls.users['regular']
        cls.users['invalid_email'] = UserFactory(profile=None, invalid_email=True)

    def test_redirect_if_has_profile(self):
        # The view is expected to redirected authenticated users who already
        # have a profile to the profile settings page.
        expected_url = reverse_lazy('profile_settings', kwargs={
            'pk': self.user_with_profile.profile.pk,
            'slug': self.user_with_profile.profile.autoslug,
        })
        for lang in self.view_page.explicit_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, user=self.user_with_profile, status='*')
                self.assertRedirects(page.response, expected_url)

    def test_page_title(self):
        # The page is expected to be titled "Settings" for all users.
        expected_text = {
            'en': "Settings",
            'eo': "Agordoj",
        }
        for lang in expected_text:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                self.assertEqual(page.get_heading_text(), expected_text[lang])

    def test_page_structure(self):
        test_data = [
            ('primary', {'en': "Password", 'eo': "Pasvorto"}),
            ('primary', {'en': "Username", 'eo': "Salutnomo"}),
            ('primary', {'en': "Email", 'eo': "Retadreso"}),
            ('warning', {'en': "Agreement", 'eo': "Interkonsento"}),
            ('warning', {'en': "Pasporta Servo Account", 'eo': "Konto ĉe Pasporta Servo"}),
        ]
        unexpected_nav_url = {
            'en': ('/profile/', '/edit/'),
            'eo': ('/profilo/', '/aktualigi/'),
        }
        for lang in unexpected_nav_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                sections = page.get_sections()
                # The account settings page is expected to have exactly 5 sections.
                self.assertLength(sections, 5)
                # Verify the order, headings, and colors of these sections.
                for i, section in enumerate(sections):
                    with self.subTest(section=i+1):
                        self.assertEqual(page.get_section_heading(section), test_data[i][1][lang])
                        self.assertEqual(page.get_section_color(section), test_data[i][0])
                # The page is not expected to have a profile navigation button.
                self.assertLength(
                    page.pyquery(
                        "a"
                        + f"[href^='{unexpected_nav_url[lang][0]}']"
                        + f"[href$='{unexpected_nav_url[lang][1]}']"
                    ), 0
                )

    def basic_section_tests(
            self, page, expected_heading, expected_urls, expected_texts, expected_css_classes,
    ):
        section = page.get_section_by_heading(expected_heading)
        self.assertLength(section, 1)
        # The page's section is expected to have the given number of links
        # (typically one or two).
        button_elements = section.find("a")
        self.assertLength(button_elements, len(expected_urls))
        for i in range(len(button_elements)):
            with self.subTest(link=str(expected_urls[i])):
                # Verify the expected target URL of the link.
                self.assertEqual(button_elements.eq(i).attr("href"), expected_urls[i])
                # Verify that the expected CSS classes are set on the link.
                if len(button_elements) == 1:
                    expected_classes = expected_css_classes
                else:
                    expected_classes = expected_css_classes[i]
                for cls in expected_classes:
                    self.assertCssClass(button_elements.eq(i), cls)
                if "btn" not in expected_classes:
                    self.assertFalse(button_elements.eq(i).has_class("btn"))
                # Verify that the link has the expected text.
                self.assertEqual(button_elements.eq(i).text(), expected_texts[i])
        return section

    def test_password_section(self):
        # The password settings section is expected to be titled "Password"
        # and contain one action link styled as a button.
        expected_url = reverse_lazy('password_change')
        expected_text = {
            'en': ("Password", "Change password"),
            'eo': ("Pasvorto", "Ŝanĝi pasvorton"),
        }
        for lang in expected_text:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, section=expected_text[lang][0])
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                self.basic_section_tests(
                    page, expected_text[lang][0],
                    [expected_url], [expected_text[lang][1]],
                    ["btn", "btn-default"],
                )

    def test_username_section(self):
        # The username settings section is expected to be titled "Username"
        # and contain one action link styled as a button as well as the user's
        # current username, properly HTML-encoded.
        expected_url = reverse_lazy('username_change')
        expected_text = {
            'en': ("Username", "Change username"),
            'eo': ("Salutnomo", "Ŝanĝi salutnomon"),
        }
        for lang in expected_text:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, section=expected_text[lang][0])
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                section = self.basic_section_tests(
                    page, expected_text[lang][0],
                    [expected_url], [expected_text[lang][1]],
                    ["btn", "btn-default"],
                )
                self.assertIn(self.user.username, cast(str, section.text()))
                self.assertNotIn(self.user.username, cast(str, section.html()))

    def test_email_section(self):
        # The email settings section is expected to be titled "Email"
        # and contain one action link styled as a button, the user's
        # current email address, a warning icon if the email is invalid,
        # and a corresponding help text.
        expected_url = reverse_lazy('email_update')
        expected_text = {
            'en': ("Email", "Update account email"),
            'eo': ("Retadreso", "Ŝanĝi retadreson por konto"),
        }
        for user_tag in self.users:
            for lang in expected_text:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang, section=expected_text[lang][0])
                ):
                    page = self.view_page.open(
                        self, self.users[user_tag], reuse_for_lang=lang)
                    section = self.basic_section_tests(
                        page, expected_text[lang][0],
                        [expected_url], [expected_text[lang][1]],
                        ["btn", "btn-default"],
                    )
                    # The user's email address and an explanation about usage of this
                    # address are expected to be displayed.
                    if user_tag != 'invalid_email':
                        self.assertIn(self.users[user_tag].email, section.text())
                        help_text_assertion = self.assertEqual
                    else:
                        self.assertIn(self.users[user_tag]._clean_email, section.text())
                        self.assertNotIn(settings.INVALID_PREFIX, section.text())
                        help_text_assertion = self.assertStartsWith
                    help_text_assertion(
                        section.find(".help-block").text(),
                        {
                            'en': "We send e-mails to this address. "
                                  + "It will never be public.",
                            'eo': "Ni sendas retmesaĝojn al tiu ĉi retpoŝta adreso. "
                                  + "Ĝi neniam estos publika.",
                        }[lang]
                    )
                    # If the user's email address is marked as invalid, an additional
                    # explanation text is expected to be displayed. If the email is
                    # valid, no such text is expected.
                    explanation_help_text = {
                        'en': "When we tried to mail it, the response was an error.",
                        'eo': "Kiam ni provis komuniki al ĝi, la respondo estis eraro.",
                    }[lang]
                    explanation_element = (
                        section
                        .find(".help-block")
                        .find("*")
                        .filter(
                            lambda i, this, content=explanation_help_text:
                            PyQuery(this).text() == content
                        )
                    )
                    if user_tag != 'invalid_email':
                        self.assertLength(explanation_element, 0)
                    else:
                        self.assertLength(explanation_element, 1)
                        self.assertCssClass(explanation_element, "text-danger")
                    # TODO: Test for the warning icon if email is invalid.

    def test_agreement_section(self):
        # The agreement settings section is expected to be titled "Agreement"
        # and contain one link to the text of the agreement.
        expected_url = reverse_lazy('agreement')
        expected_text = {
            'en': ("Agreement", "agreement between you and Pasporta Servo."),
            'eo': ("Interkonsento", "kontrakto inter vi kaj Pasporta Servo."),
        }
        for lang in expected_text:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, section=expected_text[lang][0])
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                expected_full_url = f'{expected_url}?' + urlencode({
                    settings.REDIRECT_FIELD_NAME: self.view_page.explicit_url[lang],
                })
                self.basic_section_tests(
                    page, expected_text[lang][0],
                    [expected_full_url], [expected_text[lang][1]],
                    [],
                )

    def test_membership_section(self):
        # The membership settings section is expected to be titled
        # "Pasporta Serco Account" and contain two action links, both
        # styled as buttons.
        expected_urls = [reverse_lazy('profile_create'), reverse_lazy('account_delete')]
        unexpected_url = {
            'en': ('/profile/', '/delete/'),
            'eo': ('/profilo/', '/forigi/'),
        }
        expected_texts = {
            'en': ("Pasporta Servo Account", ["Create profile", "Close account"]),
            'eo': ("Konto ĉe Pasporta Servo", ["Krei profilon", "Fermi konton"]),
        }
        expected_css = [
            ["btn", "btn-success"],
            ["btn", "btn-danger"],
        ]
        for lang in expected_texts:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, section=expected_texts[lang][0])
            ):
                page = self.view_page.open(self, self.user, reuse_for_lang=lang)
                section = self.basic_section_tests(
                    page, expected_texts[lang][0],
                    expected_urls, expected_texts[lang][1],
                    expected_css,
                )
                # The section is not expected to have a profile deletion button.
                profile_delete_button_element = section.find(
                    "a"
                    + f"[href^='{unexpected_url[lang][0]}']"
                    + f"[href$='{unexpected_url[lang][1]}']"
                )
                self.assertLength(profile_delete_button_element, 0)
