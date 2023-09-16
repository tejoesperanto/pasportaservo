from random import sample

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import override_settings, tag
from django.urls import reverse

from django_countries.data import COUNTRIES
from pyquery import PyQuery

from .. import with_type_hint
from ..factories import AdminUserFactory, StaffUserFactory, UserFactory
from .pages import HomePage, OkayPage
from .testcasebase import BasicViewTests


class HeroViewTemplateTestsMixin(with_type_hint(BasicViewTests)):
    view_page: type[HomePage] | type[OkayPage]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # A supervisor is someone who can change the data of the users in a
        # specific country (or countries).
        cls.users['supervisor'] = UserFactory()
        for c in sample(list(COUNTRIES), 2):
            Group.objects.get_or_create(name=c)[0].user_set.add(cls.users['supervisor'])
        # An admin or superuser is someone who can change everyone's data
        # (in any country).
        cls.users['admin'] = AdminUserFactory(profile=None, is_staff=False)
        # A staff user can login to the administrative interface. Apart from
        # that, there is no additional functionality in the website itself.
        cls.users['staff'] = StaffUserFactory(profile=None)
        # A full admin is a staff superuser.
        cls.users['full-admin'] = AdminUserFactory(profile=None, is_staff=True)

    def test_searchbox(self):
        # When the page is accessed without any redirection parameter, it is
        # expected to show a search box.
        for lang in ['en', 'eo']:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
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

    def test_hero_header(self):
        # When the user is not authenticated, the view's header is expected
        # to have only the "login" and "register" links. More detailed tests
        # are in `test_view_header_unauthenticated_user`.
        page = self.view_page.open(self)
        link_elements = page.get_header_links()
        self.assertLength(link_elements, 2)

        # When the user is logged in, the view's header is expected to have
        # several session and profile links – more detailed tests are in
        # `test_view_header_logged_in_user`. In addition, if the user is a
        # "full admin" with access to the administrative interface, a link
        # to this interface is expected in the header.
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
                    page = self.view_page.open(self, user=self.users[user_tag])
                    link_elements = page.get_header_links()
                    admin_element = page.get_nav_element('admin')
                    if self.users[user_tag].is_superuser and self.users[user_tag].is_staff:
                        self.assertLength(link_elements, 5)
                        self.assertEqual(admin_element.text(), expected_admin_text[lang])
                        self.assertEqual(
                            admin_element.find("a").attr("href"),
                            reverse('admin:index')
                        )
                    else:
                        self.assertLength(link_elements, 4)
                        self.assertLength(admin_element, 0)


@tag('views', 'views-general', 'views-home')
class HomeViewTests(HeroViewTemplateTestsMixin, BasicViewTests):
    view_page = HomePage

    def test_view_structure(self):
        for user in [None, self.user]:
            for lang in ['en', 'eo']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user="authenticated" if user else "anonymous", lang=lang)
                ):
                    page = self.view_page.open(self, user=user)

                    # The home view is expected to have 2 general headings, followed by
                    # a search box (its more detailed tests are in `test_searchbox`).
                    heading_elements = page.get_headings()
                    self.assertLength(heading_elements, 2)
                    self.assertEqual(heading_elements.eq(0).attr("id"), "title")
                    self.assertEqual(heading_elements.eq(0).attr("aria-level"), "1")
                    self.assertEqual(heading_elements.eq(0).text(), "Pasporta Servo")
                    self.assertEqual(heading_elements.eq(1).attr("id"), "subtitle")
                    self.assertEqual(heading_elements.eq(1).attr("aria-level"), "2")
                    self.assertEqual(
                        heading_elements.eq(1).text(),
                        {
                            'en': "The famous hosting service for Esperanto-speakers",
                            'eo': "La fama gastiga servo por esperantistoj",
                        }[lang]
                    )
                    self.assertCssClass(heading_elements.parent().next_all(), "search-container")

                    # A promo element is expected to be present. We do not verify its
                    # exact contents.
                    promo_element = page.pyquery("#promo-pitch")
                    self.assertLength(promo_element, 1)
                    self.assertEqual(promo_element.attr("role"), "note")
                    self.assertNotEqual(promo_element.text(), "")
                    # Overly simple verification for Esperanto promo text.
                    if lang == 'eo':
                        self.assertIn("ĉ", promo_element.text())
                    else:
                        self.assertNotIn("ĉ", promo_element.text())

                    # A link to the map of hosts is expected to be present.
                    explore_element = page.pyquery("#home-explore")
                    self.assertLength(explore_element, 1)
                    self.assertEqual(
                        explore_element.text(),
                        {
                            'en': "Explore the map of the hosts",
                            'eo': "Esploru la mapon de la gastigantoj"
                        }[lang]
                    )
                    self.assertEqual(explore_element.find("a").attr("href"), reverse('world_map'))

                    # A container for news and usage is expected to be present and to
                    # be empty by default. More detailed tests are in `test_news_block`
                    # and `test_usage_block`,
                    explain_element = page.pyquery("#home-explain")
                    self.assertEqual(explain_element.text(), "")

                    # The home view is expected to include various social links.
                    test_data = {
                        'social-networks': {
                            "fb": (
                                "facebook.com",
                                {
                                    'en': "Pasporta Servo at Facebook",
                                    'eo': "Pasporta Servo ĉe Facebook",
                                }
                            ),
                            "tw": (
                                "twitter.com",
                                {
                                    'en': "Pasporta Servo at Twitter",
                                    'eo': "Pasporta Servo ĉe Twitter",
                                }
                            ),
                            "tg": (
                                "telegramo.org",
                                {
                                    'en': "Discuss Pasporta Servo on Telegram",
                                    'eo': "Diskutoj pri Pasporta Servo per Telegramo",
                                }
                            ),
                            "yt": (
                                "youtu.be",
                                {
                                    'en': "About Pasporta Servo, on YouTube",
                                    'eo': "Pri Pasporta Servo, ĉe YouTube",
                                }
                            ),
                        },
                        'social-contact': {
                            "e": (
                                "mailto:saluton [cxe] pasportaservo.org",
                                {
                                    'en': "Contact us via email",
                                    'eo': "Kontaktu nin per retpoŝto",
                                }
                            ),
                            "i": (
                                "github.com",
                                {
                                    'en': "Your ideas and suggestions",
                                    'eo': "Viaj ideoj kaj proponoj",
                                }
                            ),
                            "s": (
                                "github.com",
                                {
                                    'en': "Pasporta Servo's source code",
                                    'eo': "Fontkodo de Pasporta Servo",
                                }
                            ),
                        }
                    }
                    for social_tag in test_data:
                        social_element = page.pyquery(f".social-links.{social_tag}")
                        with self.subTest(tag=social_tag):
                            self.assertLength(social_element, 1)
                            social_link_elements = social_element.find("a")
                            self.assertLength(social_link_elements, len(test_data[social_tag]))
                            for social_particular_tag in test_data[social_tag]:
                                expected_link, expected_title = (
                                    test_data[social_tag][social_particular_tag]
                                )
                                with self.subTest(
                                        tag=f"{social_tag}/{social_particular_tag}",
                                        link=expected_link,
                                ):
                                    def by_title(i, this, *, title=expected_title[lang]):
                                        return PyQuery(this).attr("title") == title
                                    link_element = social_link_elements.filter(by_title)
                                    self.assertLength(link_element, 1)
                                    if not expected_link.startswith('mailto:'):
                                        self.assertIn(f"{expected_link}/", link_element.attr("href"))
                                        self.assertStartsWith(link_element.attr("href"), "https://")
                                        self.assertEqual(link_element.attr("rel"), "external noreferrer")
                                    else:
                                        self.assertEqual(link_element.attr("href"), expected_link)
                                        self.assertIsNone(link_element.attr("rel"))
                                    self.assertEqual(link_element.text(), f"[ {expected_title[lang]} ]")
                                    link_element.find(".sr-only").text("")
                                    self.assertEqual(link_element.text(), "")

    def test_news_block(self):
        # TODO
        pass

    def test_usage_block(self):
        # TODO
        pass


@tag('views', 'views-general')
class OkayViewTests(HeroViewTemplateTestsMixin, BasicViewTests):
    view_page = OkayPage

    def test_headings(self):
        # The view is expected to have 2 headings:
        # a 200 (HTTP status code) and the localized text "OK".
        for lang in ['en', 'eo']:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                heading_elements = page.get_headings()
                self.assertLength(heading_elements, 2)
                self.assertEqual(heading_elements.eq(0).attr("id"), "title")
                self.assertEqual(heading_elements.eq(0).attr("aria-level"), "1")
                self.assertEqual(heading_elements.eq(0).text(), "200")
                self.assertEqual(heading_elements.eq(1).attr("id"), "subtitle")
                self.assertEqual(heading_elements.eq(1).attr("aria-level"), "2")
                # No reason message is expected in the second heading.
                self.assertEqual(
                    heading_elements.eq(1).text(),
                    {'en': "OK", 'eo': "Enordas"}[lang]
                )

    def test_back_button(self):
        # When the page is accessed with a redirection parameter, it is expected
        # to show a back button leading to the redirection target, instead of
        # the search box.
        # When no redirection parameter is specified, a search box is expected
        # to be shown; tested in `test_searchbox`.
        for lang in ['en', 'eo']:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, redirect_to='sit')
                container_element = page.get_hero_content()
                self.assertLength(container_element.find("[role='search']"), 0)
                link_element = container_element.find("a")
                self.assertLength(link_element, 1)
                self.assertEqual(
                    link_element.text(),
                    {'en': "Back to previous page", 'eo': "Reen al antaŭa paĝo"}[lang]
                )
                self.assertCssClass(link_element, "btn")
                self.assertCssClass(link_element, "btn-default")
                self.assertCssClass(link_element, "btn-lg")
                self.assertEqual(link_element.attr("href"), "sit")

                # When no redirection target is provided, the back button is
                # expected to be not shown.
                page = self.view_page.open(self, redirect_to='')
                container_element = page.get_hero_content()
                self.assertLength(container_element.find("[role='search']"), 1)
                self.assertLength(container_element.find("a"), 0)

                # When the provided redirection target is insecure, the back
                # button is expected to be not shown.
                page = self.view_page.open(self, redirect_to='//fly')
                container_element = page.get_hero_content()
                self.assertLength(container_element.find("[role='search']"), 1)
                self.assertLength(container_element.find("a"), 0)
