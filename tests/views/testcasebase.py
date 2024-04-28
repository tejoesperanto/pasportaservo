from typing import cast
from urllib.parse import urlencode

from django.conf import settings
from django.test import override_settings
from django.urls import reverse_lazy
from django.utils.functional import Promise

from django_webtest import WebTest

from ..assertions import AdditionalAsserts
from ..factories import UserFactory
from .pages.base import PageTemplate


class BasicViewTests(AdditionalAsserts, WebTest):
    view_page = PageTemplate

    def run(self, result=None):
        if self.__class__ is BasicViewTests:
            # Do not run any tests directly from the base test suite.
            return result
        else:
            return super().run(result)

    @classmethod
    def setUpClass(cls):
        cls.users_definition = {
            'basic': {
                'email': "salutator@test.pasportaservo.org",
                'avatar_url': "/static/img/avatar-unknown.png",
            },
            'regular': {
                'email': "mediastinus@test.pasportaservo.org",
                'avatar_url': "https://www.gravatar.com/avatar/"
                              + "96cc8ee60515664247821d27fb6f2867?d=mm&s=140",
            },
        }
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        basic_user = UserFactory(email=cls.users_definition['basic']['email'], profile=None)
        cls.user = UserFactory(email=cls.users_definition['regular']['email'])
        cls.users = {
            'basic': basic_user,
            'regular': cls.user,
        }

    @property
    def url(self) -> Promise:
        return self.view_page.url

    def test_view_url(self):
        # Verify that the view can be found at the expected URL.
        if self.url is not None:
            if self.view_page.redirects_unauthenticated:
                response = self.app.get(self.url, status='*', user=self.user)
            else:
                response = self.app.get(self.url, status='*')
            self.assertEqual(response.status_code, 200)

        for lang, expected_url in self.view_page.explicit_url.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, attempted=expected_url)
            ):
                if self.view_page.redirects_unauthenticated:
                    response = self.app.get(expected_url, status='*', user=self.user)
                else:
                    response = self.app.get(expected_url, status='*')
                self.assertEqual(response.status_code, 200)
                if self.view_page.view_class is not None:
                    self.assertTrue('view' in response.context)
                    self.assertIsInstance(
                        response.context['view'], self.view_page.view_class)
                else:
                    # In some special cases, such as error responses or flat pages,
                    # there is no `view` variable in the context of the response.
                    self.assertFalse('view' in response.context)

    def test_view_title(self):
        # Verify that the view has the expected <title> element.
        for lang in self.view_page.title:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(
                    self,
                    user=self.user if self.view_page.redirects_unauthenticated else None)
                self.assertHTMLEqual(
                    cast(str, page.pyquery("title").html()),
                    self.view_page.title[lang]
                )

    def test_view_header_unauthenticated_user(self):
        if self.view_page.redirects_unauthenticated:
            view_name = getattr(self.view_page.view_class, '__name__ ', 'This view')
            self.skipTest(f'{view_name} is expected to redirect non-authenticated users')

        # When the user is not authenticated, the view's header is expected
        # to have "login" and "register" links, no username or link to profile,
        # and no use notice.
        test_data = self.view_page.header_logged_out
        for lang in test_data:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                if page.url != '/':
                    redirect_query = '?' + urlencode({settings.REDIRECT_FIELD_NAME: page.url})
                else:
                    redirect_query = ''
                session_element = page.get_nav_element("session")
                self.assertEqual(session_element.text(), test_data[lang]['session']['text'])
                self.assertEqual(
                    session_element.find("a").attr("href"),
                    test_data[lang]['session']['url'] + redirect_query
                )
                profile_element = page.get_nav_element("profile")
                self.assertEqual(profile_element.text(), test_data[lang]['profile']['text'])
                self.assertEqual(
                    profile_element.find("a").attr("href"),
                    test_data[lang]['profile']['url'] + redirect_query
                )
                self.assertLength(profile_element.find("img"), 0)
                if self.view_page.use_notice:
                    self.assertEqual(
                        page.get_use_notice_text(),
                        test_data[lang]['use_notice'])
                else:
                    self.assertEqual(page.get_use_notice_text(), "")

    def test_view_header_logged_in_user(self):
        if self.view_page.redirects_logged_in:
            view_name = getattr(self.view_page.view_class, '__name__ ', 'This view')
            self.skipTest(f'{view_name} is expected to redirect authenticated users')

        # When the user is logged in, the view's header is expected to have
        # a "logout" link, a link to profile with the user's avatar, links to
        # the account settings and the inbox, and a use notice in some cases.
        test_data = self.view_page.header_logged_in
        for user_tag in self.users:
            for lang in test_data:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=self.users[user_tag])
                    user_has_profile = hasattr(self.users[user_tag], 'profile')

                    for nav_part in test_data[lang].keys() - {'profile', 'use_notice'}:
                        with self.subTest(navigation=nav_part):
                            element = page.get_nav_element(nav_part)
                            # Verify that the visible text of the navigation element is
                            # the expected one.
                            expected_text = test_data[lang][nav_part]['text']
                            if isinstance(expected_text, dict):
                                expected_text = expected_text[user_has_profile]
                            element.find(".sr-only").text("")
                            self.assertEqual(element.text(), expected_text)
                            # Verify that the navigation element links to the expected
                            # page (parametrization, such as the profile ID, is ignored
                            # at this point).
                            element_href = element.find("a").attr("href")
                            expected_url = test_data[lang][nav_part]['url']
                            if isinstance(expected_url, dict):
                                expected_url = expected_url[user_has_profile]
                            if '...' in expected_url:
                                expected_url_prefix, expected_url_suffix = expected_url.split('...')
                                self.assertStartsWith(element_href, expected_url_prefix)
                                self.assertEndsWith(element_href, expected_url_suffix)
                            else:
                                self.assertEqual(element_href, expected_url)

                    # Verify that the profile navigation element displays the
                    # user's avatar and links to the user's public profile
                    # (or the profile creation page in case the user doesn't
                    # have one already).
                    nav_part = 'profile'
                    with self.subTest(navigation=nav_part):
                        profile_link_element = page.get_nav_element(nav_part).children("a")
                        self.assertLength(profile_link_element, 1)
                        self.assertEqual(
                            profile_link_element.attr("title"),
                            test_data[lang][nav_part]['text']
                        )
                        self.assertNotEqual(
                            profile_link_element.text(),
                            self.view_page.header_logged_out[lang][nav_part]['text']
                        )
                        if user_has_profile:
                            self.assertStartsWith(
                                profile_link_element.attr("href"),
                                test_data[lang][nav_part]['url'][True]
                            )
                        else:
                            self.assertEqual(
                                profile_link_element.attr("href"),
                                test_data[lang][nav_part]['url'][False]
                            )
                        profile_avatar_element = profile_link_element.find("img")
                        if 'avatar_url' in self.users_definition.get(user_tag, {}):
                            self.assertEqual(
                                profile_avatar_element.attr("src"),
                                self.users_definition[user_tag]['avatar_url']
                            )
                        self.assertIn(
                            self.users[user_tag].username,
                            profile_avatar_element.attr("aria-label")
                        )

                    # Verify that the page includes a fair use notice if one is
                    # required.
                    if self.view_page.use_notice:
                        if user_has_profile:
                            self.assertStartsWith(
                                page.get_use_notice_text(),
                                test_data[lang]['use_notice'][True]
                            )
                        else:
                            self.assertEqual(
                                page.get_use_notice_text(),
                                test_data[lang]['use_notice'][False]
                            )
                    else:
                        self.assertEqual(page.get_use_notice_text(), "")

    def test_view_footer(self):
        # The view's footer is expected to have several links to general pages,
        # as well as information about the deployment environment and the
        # logged-in user (unless it is production).
        test_data = {
            'about': {'en': "About us", 'eo': "Pri ni"},
            'terms_conditions': {'en': "Terms", 'eo': "Kondiĉoj"},
            'privacy_policy': {'en': "Privacy", 'eo': "Privateco"},
            'faq': {'en': "FAQ", 'eo': "Oftaj demandoj"},
        }
        test_users = []
        if not self.view_page.redirects_unauthenticated:
            test_users.append(None)
        if not self.view_page.redirects_logged_in:
            test_users.append(self.user)

        for user in test_users:
            for lang in ['en', 'eo']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    for url in test_data:
                        with self.subTest(url=url):
                            general_link_element = page.get_footer_element(url)
                            self.assertLength(general_link_element, 1)
                            self.assertEqual(general_link_element.text(), test_data[url][lang])
                    env_text = page.get_footer_element("env-info").text()
                    self.assertStartsWith(env_text, settings.ENVIRONMENT)
                    if user is not None:
                        self.assertIn(user.username, env_text)
                    else:
                        self.assertNotIn({'en': "user", 'eo': "uzanto"}[lang], env_text)

    def test_view_template(self):
        # Verify that the view uses the expected template.
        page = self.view_page.open(
            self, user=self.user if self.view_page.redirects_unauthenticated else None)
        self.assertTemplateUsed(page.response, self.view_page.template)

    def test_redirect_if_logged_out(self):
        view_name = getattr(self.view_page.view_class, '__name__ ', 'This view')

        expected_url = reverse_lazy('login')
        for lang in self.view_page.explicit_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                # Verify that the view redirects unauthenticated users to the
                # login page if required.
                page = self.view_page.open(self, status='*')
                if self.view_page.redirects_unauthenticated:
                    self.assertEqual(
                        page.response.status_code, 302,
                        msg=f"{view_name} is expected to redirect non-authenticated users"
                    )
                    self.assertURLEqual(
                        page.response.location,
                        f'{expected_url}?' + urlencode({
                            settings.REDIRECT_FIELD_NAME: self.view_page.explicit_url[lang],
                        })
                    )
                else:
                    self.assertEqual(
                        page.response.status_code, 200,
                        msg=f"{view_name} is expected to be accessible to non-authenticated users"
                    )

                # Verify that if required, the view redirects unauthenticated
                # users to the login page also when an explicit redirection
                # target is provided.
                page = self.view_page.open(self, redirect_to='/and-then', status='*')
                if self.view_page.redirects_unauthenticated:
                    self.assertEqual(
                        page.response.status_code, 302,
                        msg=f"{view_name} is expected to redirect non-authenticated users"
                    )
                    self.assertURLEqual(
                        page.response.location,
                        f'{expected_url}?' + urlencode({
                            settings.REDIRECT_FIELD_NAME:
                                f'{self.view_page.explicit_url[lang]}?'
                                + urlencode({settings.REDIRECT_FIELD_NAME: '/and-then'}),
                        })
                    )
                else:
                    self.assertEqual(
                        page.response.status_code, 200,
                        msg=f"{view_name} is expected to be accessible to non-authenticated users"
                    )
