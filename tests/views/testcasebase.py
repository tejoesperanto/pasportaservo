from enum import Enum
from typing import Any, Literal, Optional, Self, cast, overload
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import override_settings
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils.functional import Promise

from django_webtest import WebTest, _notgiven as WEBTEST_USER_NOT_GIVEN

from hosting.models import PasportaServoUser

from .. import DjangoWebtestResponse, with_type_hint
from ..assertions import AdditionalAsserts
from ..factories import UserFactory
from .pages.base import PageHeroTemplate, PageTemplate


class Sentinel(Enum):
    NOT_GIVEN = object()  # TODO: Replace by sentinel() in Python 3.15.


class ViewTestingBase(AdditionalAsserts, WebTest):
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
                              + "7d19d453edd2945c82f1be4a753f3b53abcc5b685edc749fd484b3bd7effee77"
                              + "?d=mp&s=140",
            },
        }
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        basic_user = UserFactory.create(email=cls.users_definition['basic']['email'], profile=None)
        cls.user = UserFactory.create(email=cls.users_definition['regular']['email'])
        cls.users = {
            'basic': basic_user,
            'regular': cls.user,
        }


class ViewAsserts(with_type_hint(ViewTestingBase)):
    @overload
    def _user_for_page_request(
            self: Self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
            raw_request: Literal[False] = False,
    ) -> PasportaServoUser | None:
        ...

    @overload
    def _user_for_page_request(
            self: Self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
            raw_request: Literal[True] = True,
    ) -> PasportaServoUser | object:
        ...

    def _user_for_page_request(
            self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
            raw_request: bool = False,
    ):
        if user is Sentinel.NOT_GIVEN:
            if view_page.redirects_unauthenticated:
                app_user = self.user
            else:
                app_user = WEBTEST_USER_NOT_GIVEN if raw_request else None
        else:
            app_user = user
        return app_user

    def _assert_view_url_main(
            self, view_page: type[PageTemplate],
            expected_url: str | Promise,
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        response: DjangoWebtestResponse
        app_user = self._user_for_page_request(view_page, user, raw_request=True)
        response = self.app.get(expected_url, status='*', user=app_user)
        self.assertEqual(response.status_code, 200)

    def _assert_view_url_alt(
            self, view_page: type[PageTemplate],
            *,
            url_kwargs_per_tag: Optional[dict[str, dict[str, Any]]] = None,
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        response: DjangoWebtestResponse
        url_kwargs = url_kwargs_per_tag or {}
        app_user = self._user_for_page_request(view_page, user, raw_request=True)
        extra_info = ("URL resolved to a valid path but the view failed to load")
        if app_user is not None and app_user is not WEBTEST_USER_NOT_GIVEN:
            extra_info += " for the given user"

        if view_page.alternative_urls is not None:
            for url_tag in view_page.alternative_urls:
                expected_url = view_page.get_complete_url(url_tag, url_kwargs.get(url_tag))
                with self.subTest(tag=url_tag):
                    self.assertNotRaises(NoReverseMatch, lambda: str(expected_url))
                    with self.subTest(attempted=expected_url):
                        response = self.app.get(expected_url, status='*', user=app_user)
                        extra_info_for_tag = extra_info + (
                            f"{' and' if extra_info.endswith('user') else ''}"
                            " for the given parameters" if url_tag in url_kwargs else ""
                        )
                        self.assertEqual(response.status_code, 200, msg=extra_info_for_tag)

    def _assert_view_explicit_url(
            self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        response: DjangoWebtestResponse
        app_user = self._user_for_page_request(view_page, user, raw_request=True)

        for lang, expected_url in view_page.explicit_url.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, attempted=expected_url)
            ):
                response = self.app.get(expected_url, status='*', user=app_user)
                self.assertEqual(response.status_code, 200)
                if view_page.view_class is not None:
                    self.assertTrue('view' in response.context)
                    self.assertIsInstance(
                        response.context['view'], view_page.view_class)
                else:
                    # In some special cases, such as error responses or flat pages,
                    # there is no `view` variable in the context of the response.
                    self.assertFalse('view' in response.context)

    def _assert_view_title(
            self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        app_user = self._user_for_page_request(view_page, user)
        for lang in view_page.title:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = view_page.open(self, user=app_user, reuse_for_lang=lang)
                self.assertHTMLEqual(
                    cast(str, page.pyquery("title").html()),
                    view_page.title[lang]
                )

    def _assert_view_title_alt(
            self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        app_user = self._user_for_page_request(view_page, user)
        if view_page.alternative_titles is not None:
            for url_tag in view_page.alternative_titles:
                for lang in view_page.alternative_titles[url_tag]:
                    with (
                        override_settings(LANGUAGE_CODE=lang),
                        self.subTest(tag=url_tag, lang=lang)
                    ):
                        page = view_page.open(
                            self, user=app_user, url_tag=url_tag, reuse_for_lang=lang)
                        self.assertHTMLEqual(
                            cast(str, page.pyquery("title").html()),
                            view_page.alternative_titles[url_tag][lang]
                        )

    def _assert_view_open_graph_tags(
            self, view_page: type[PageTemplate],
            url_tag: str = 'base', url_params: Optional[dict[str, Any]] = None,
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
            **customizations,
    ):
        first_site = Site.objects.get(id=1)
        first_site.name, first_site.domain = 'OGPTestServer', 'test.domain'
        first_site.save(update_fields=['name', 'domain'])
        app_user = self._user_for_page_request(view_page, user)
        for lang in view_page.explicit_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = view_page.open(
                    self, user=app_user, url_tag=url_tag, url_params=url_params)
                pyquery = page.pyquery
                self.assertEqual(
                    pyquery("meta[property='og:title']").attr("content"),
                    customizations.get('title', view_page.title)[lang])
                self.assertEqual(
                    pyquery("meta[property='og:type']").attr("content"),
                    customizations.get('type', "website"))
                self.assertEqual(
                    pyquery("meta[property='og:url']").attr("content"),
                    f'http://test.domain'
                    f'{customizations.get('page_url', view_page.explicit_url)[lang]}')
                self.assertEqual(
                    pyquery("meta[property='og:locale']").attr("content"),
                    lang)
                image_url = cast(str, customizations.get(
                    'image', '/static/img/social_media_thumbnail_main.png'))
                image_url = image_url.replace('[DOMAIN]', 'test.domain')
                ogp_image_element = pyquery("meta[property='og:image']")
                self.assertStartsWith(
                    ogp_image_element.attr("content"),
                    f'http://test.domain{image_url}' if image_url.startswith('/') else image_url)
                image_alt_url = cast(str | None, customizations.get('image_alt'))
                if image_alt_url:
                    image_alt_url = image_alt_url.replace('[DOMAIN]', 'test.domain')
                    expected_url = (
                        f'http://test.domain{image_alt_url}' if image_alt_url.startswith('/')
                        else image_alt_url)
                    self.assertLength(ogp_image_element, 2)
                    self.assertStartsWith(ogp_image_element.eq(1).attr("content"), expected_url)
                else:
                    self.assertLength(ogp_image_element, 1)

    def _assert_view_header_logged_out(self, view_page: type[PageTemplate]):
        # When the user is not authenticated, the view's header is expected
        # to have "login" and "register" links, no username or link to profile,
        # and no use notice.
        test_data = view_page.header_logged_out
        for lang in test_data:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = view_page.open(self)
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
                if view_page.use_notice:
                    self.assertEqual(
                        page.get_use_notice_text(),
                        test_data[lang]['use_notice'])
                else:
                    self.assertEqual(page.get_use_notice_text(), "")

    def _assert_view_header_logged_in(self, view_page: type[PageTemplate]):
        # When the user is logged in, the view's header is expected to have
        # a "logout" link, a link to profile with the user's avatar, links to
        # the account settings and the inbox, and a use notice in some cases.
        test_data = view_page.header_logged_in
        for user_tag in self.users:
            for lang in test_data:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = view_page.open(self, user=self.users[user_tag])
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
                            if nav_part == 'session':
                                element_target = element.find("form").attr("action")
                                self.assertEqual(
                                    cast(str, element.find("form").attr("method") or "").upper(),
                                    "POST"
                                )
                            else:
                                element_target = element.find("a").attr("href")
                            expected_url = test_data[lang][nav_part]['url']
                            if isinstance(expected_url, dict):
                                expected_url = expected_url[user_has_profile]
                            if '...' in expected_url:
                                expected_url_prefix, expected_url_suffix = expected_url.split('...')
                                self.assertStartsWith(element_target, expected_url_prefix)
                                self.assertEndsWith(element_target, expected_url_suffix)
                            else:
                                self.assertEqual(element_target, expected_url)

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
                            view_page.header_logged_out[lang][nav_part]['text']
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
                        if 'avatar_url' in getattr(self, 'users_definition', {}).get(user_tag, {}):
                            self.assertEqual(
                                profile_avatar_element.attr("src"),
                                self.users_definition[user_tag]['avatar_url']
                            )
                        self.assertIn(
                            self.users[user_tag].username,
                            cast(str, profile_avatar_element.attr("aria-label"))
                        )

                    # Verify that the page includes a fair use notice if one is
                    # required.
                    if view_page.use_notice:
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

    def _assert_view_footer(self, view_page: type[PageTemplate]):
        # The view's footer is expected to have several links to general pages,
        # as well as information about the deployment environment and the
        # logged-in user (unless it is production).
        test_data = {
            'about': {'en': "About us", 'eo': "Pri ni"},
            'terms_conditions': {'en': "Terms", 'eo': "Kondiĉoj"},
            'privacy_policy': {'en': "Privacy", 'eo': "Privateco"},
            'faq': {'en': "FAQ", 'eo': "Oftaj demandoj"},
        }
        test_users: list[PasportaServoUser | None] = []
        if not view_page.redirects_unauthenticated:
            test_users.append(None)
        if not view_page.redirects_logged_in:
            test_users.append(self.user)

        for user in test_users:
            for lang in ['en', 'eo']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user, lang=lang)
                ):
                    self.app.reset()
                    page = view_page.open(self, user=user, reuse_for_lang=lang)
                    for url in test_data:
                        with self.subTest(url=url):
                            general_link_element = page.get_footer_element(url)
                            self.assertLength(general_link_element, 1)
                            self.assertEqual(general_link_element.text(), test_data[url][lang])
                    env_text = cast(str, page.get_footer_element("env-info").text())
                    self.assertStartsWith(env_text, settings.ENVIRONMENT)
                    if user is not None:
                        username_index = env_text.find(user.username)
                        self.assertGreater(username_index, 0,
                                           msg="username not present in environment info")
                        user_tag = ([
                            key for key, defined_user in self.users.items()
                            if defined_user is user
                        ] or [None])[0]
                        if user_tag and 'supervisor' in user_tag:
                            self.assertGreater(
                                env_text.find({'en': "SV", 'eo': "LO"}[lang], username_index),
                                len(user.username),
                                msg="supervisor status not present in environment info"
                            )
                    else:
                        self.assertNotIn({'en': "user", 'eo': "uzanto"}[lang], env_text)

    def _assert_view_template(
            self, view_page: type[PageTemplate],
            user: PasportaServoUser | None | Sentinel = Sentinel.NOT_GIVEN,
    ):
        page = view_page.open(self, user=self._user_for_page_request(view_page, user))
        self.assertTemplateUsed(page.response, view_page.template)

    def _assert_view_redirect_logged_out(self, view_page: type[PageTemplate]):
        view_name = getattr(view_page.view_class, '__name__ ', 'This view')

        expected_url = reverse_lazy('login')
        for lang in view_page.explicit_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                # Verify that the view redirects unauthenticated users to the
                # login page if required.
                page = view_page.open(self, status='*')
                if view_page.redirects_unauthenticated:
                    self.assertEqual(
                        page.response.status_code, 302,
                        msg=f"{view_name} is expected to redirect non-authenticated users"
                    )
                    self.assertURLEqual(
                        page.response.location,
                        f'{expected_url}?' + urlencode({
                            settings.REDIRECT_FIELD_NAME: view_page.explicit_url[lang],
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
                page = view_page.open(self, redirect_to='/and-then', status='*')
                if view_page.redirects_unauthenticated:
                    self.assertEqual(
                        page.response.status_code, 302,
                        msg=f"{view_name} is expected to redirect non-authenticated users"
                    )
                    self.assertURLEqual(
                        page.response.location,
                        f'{expected_url}?' + urlencode({
                            settings.REDIRECT_FIELD_NAME:
                                f'{view_page.explicit_url[lang]}?'
                                + urlencode({settings.REDIRECT_FIELD_NAME: '/and-then'}),
                        })
                    )
                else:
                    self.assertEqual(
                        page.response.status_code, 200,
                        msg=f"{view_name} is expected to be accessible to non-authenticated users"
                    )


class HeroViewAsserts(with_type_hint(ViewTestingBase)):
    def _assert_searchbox(self, view_page: type[PageHeroTemplate]):
        # When the page is accessed without any redirection parameter, it is
        # expected to show a search box.
        for lang in view_page.explicit_url:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = view_page.open(self, reuse_for_lang=lang)
                container_element = page.get_hero_content()
                self.assertLength(container_element, 1)
                # An element with an ARIA role "search" is expected to be present.
                search_element = container_element.find("[id='searchform']")
                self.assertLength(search_element, 1)
                self.assertEqual(search_element.attr("role"), "search")
                self.assertCssClass(search_element, "search")
                # A form element with a search input field, using the name
                # specified in the settings, is expected to be present.
                search_form_element = search_element("form")
                self.assertLength(search_form_element, 1)
                self.assertEqual(search_form_element.attr("action"), reverse('search'))
                search_input_element = search_form_element.find("input#searchinput")
                self.assertLength(search_input_element, 1)
                self.assertEqual(search_input_element.attr("type"), "search")
                self.assertEqual(search_input_element.attr("name"), settings.SEARCH_FIELD_NAME)
                self.assertCssClass(search_input_element, "form-control")
                # A form submit element, styled as a button with a localized
                # caption "search", is expected to be present.
                search_submit_element = search_form_element.find("[type='submit']")
                self.assertLength(search_submit_element, 1)
                self.assertCssClass(search_submit_element, "btn")
                self.assertCssClass(search_submit_element, "btn-default")
                self.assertFalse(search_submit_element.has_class("btn-primary"))
                self.assertEqual(
                    search_submit_element.text(),
                    {'en': "Search", 'eo': "Serĉi"}[lang]
                )

    def _assert_view_hero_header_logged_out(self, view_page: type[PageHeroTemplate]):
        # When the user is not authenticated, the view's header is expected
        # to have only the "login" and "register" links. More detailed tests
        # are in `ViewAsserts._assert_view_header_logged_out`.
        page = view_page.open(self)
        link_elements = page.get_header_links()
        self.assertLength(link_elements, 2)

    def _assert_view_hero_header_logged_in(self, view_page: type[PageHeroTemplate]):
        # When the user is logged in, the view's header is expected to have
        # several session and profile links – more detailed tests are in
        # `ViewAsserts._assert_view_header_logged_in`. In addition, if the
        # user is a "full admin" with access to the administrative interface,
        # a link to this interface is expected in the header.
        expected_admin_text = {
            'en': "admin site",
            'eo': "administrilo",
        }
        for user_tag in self.users:
            for lang in expected_admin_text:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = view_page.open(
                        self, user=self.users[user_tag], reuse_for_lang=lang)
                    link_elements = page.get_header_links()
                    admin_element = page.get_nav_element('admin')
                    if self.users[user_tag].is_superuser and self.users[user_tag].is_staff:
                        self.assertLength(link_elements, 4)
                        self.assertEqual(admin_element.text(), expected_admin_text[lang])
                        self.assertEqual(
                            admin_element.find("a").attr("href"),
                            reverse('admin:index')
                        )
                    else:
                        self.assertLength(link_elements, 3)
                        self.assertLength(admin_element, 0)


class BasicViewTests(ViewAsserts, ViewTestingBase):
    view_page = PageTemplate

    def run(self, result=None):
        if self.__class__ is BasicViewTests:
            # Do not run any tests directly from the base test suite.
            return result
        else:
            return super().run(result)

    @property
    def url(self) -> Promise:
        return self.view_page.get_complete_url()

    def test_view_url(self):
        """
        Verifies that the view can be found at the expected URL.
        """
        if self.url is not None:
            self._assert_view_url_main(self.view_page, self.url)
        self._assert_view_url_alt(self.view_page)
        self._assert_view_explicit_url(self.view_page)

    def test_view_title(self):
        """
        Verifies that the view has the expected <title> element.
        """
        self._assert_view_title(self.view_page)
        self._assert_view_title_alt(self.view_page)

    def test_view_open_graph_tags(self):
        """
        Verifies that the view has the expected OGP <meta> tags.
        """
        self._assert_view_open_graph_tags(self.view_page)

    def test_view_header_unauthenticated_user(self):
        """
        Tests the contents of the page header shown to logged out users.
        """
        if self.view_page.redirects_unauthenticated:
            view_name = getattr(self.view_page.view_class, '__name__ ', 'This view')
            self.skipTest(f'{view_name} is expected to redirect non-authenticated users')
        self._assert_view_header_logged_out(self.view_page)

    def test_view_header_logged_in_user(self):
        """
        Tests the contents of the page header shown to logged in users.
        """
        if self.view_page.redirects_logged_in:
            view_name = getattr(self.view_page.view_class, '__name__ ', 'This view')
            self.skipTest(f'{view_name} is expected to redirect authenticated users')
        self._assert_view_header_logged_in(self.view_page)

    def test_view_footer(self):
        """
        Tests the contents of the page footer shown to the users.
        """
        self._assert_view_footer(self.view_page)

    def test_view_template(self):
        """
        Verifies that the view uses the expected template.
        """
        self._assert_view_template(self.view_page)

    def test_redirect_if_logged_out(self):
        """
        Verifies that the view redirects a logged out user to the login page
        when it is not defined as accessible to unauthenticated visitors.
        """
        self._assert_view_redirect_logged_out(self.view_page)
