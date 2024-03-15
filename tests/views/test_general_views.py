from datetime import date
from random import sample
from typing import Literal, Optional, TypedDict, cast

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.flatpages.models import FlatPage
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import Q
from django.test import override_settings, tag
from django.test.utils import CaptureQueriesContext
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.formats import localize
from django.utils.functional import classproperty

from django_countries.data import COUNTRIES
from faker import Faker
from lxml.html import HtmlComment, HtmlElement
from pyquery import PyQuery
from webtest.forms import Form as HtmlForm

from core.models import Policy
from shop.tests.factories import ProductReservationFactory

from .. import with_type_hint
from ..factories import (
    AdminUserFactory, PolicyFactory, StaffUserFactory, UserFactory,
)
from .pages import AboutPage, FAQPage, HomePage, OkayPage, PrivacyPage, TCPage
from .pages.base import PageWithTitleHeadingTemplate
from .pages.general import PageWithLanguageSwitcher
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
                page = self.view_page.open(self, reuse_for_lang=lang)
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
                    page = self.view_page.open(
                        self, user=self.users[user_tag], reuse_for_lang=lang)
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

    @property
    def params_for_test(self):
        return {
            'users': [
                ("anonymous", None),
                ("authenticated", self.user),
            ],
            'langs': ['en', 'eo'],
        }

    def test_page_title(self):
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)

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
                    self.assertCssClass(
                        heading_elements.parent().next_all(),
                        "search-container"
                    )

    def test_page_structure(self):
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)

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
                    self.assertEqual(
                        explore_element.find("a").attr("href"),
                        reverse('world_map')
                    )
                    # This link is expected to be placed after the promo element.
                    self.assertEqual(
                        promo_element.next().attr("id"),
                        explore_element.attr("id")
                    )

                    # A container for news and usage is expected to be present and to
                    # be empty by default. More detailed tests are in `test_news_block`
                    # and `test_usage_block`,
                    explain_element = page.pyquery("#home-explain")
                    self.assertEqual(explain_element.text(), "")
                    # This container is expected to be placed directly after the link
                    # to the map of hosts.
                    self.assertEqual(
                        explore_element.next().attr("id"),
                        explain_element.attr("id")
                    )

    def test_social_buttons(self):
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)

                    # The home view is expected to include various social links.
                    test_data: dict[str, dict[str, tuple[str, dict[str, str]]]] = {
                        'social-networks': {
                            "fb": (
                                "facebook.com",
                                {
                                    'en': "Pasporta Servo at Facebook",
                                    'eo': "Pasporta Servo ĉe Facebook",
                                }
                            ),
                            "ms": (
                                "esperanto.masto.host",
                                {
                                    'en': "Pasporta Servo at Mastodon",
                                    'eo': "Pasporta Servo ĉe Mastodon",
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

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_support_button(self):
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    # Do not reuse the cached pages, load clean instances.
                    page = self.view_page.open(self, user=user)

                    # The home view is expected to include a "support us" link,
                    # styled as a button.
                    support_element = page.pyquery(".social-support")
                    support_link_element = support_element.find("a")
                    self.assertLength(support_link_element, 1)
                    self.assertEqual(
                        support_link_element.attr("href"),
                        "https://buymeacoffee.com/pasportaservo"
                    )
                    self.assertEqual(support_link_element.attr("rel"), "external noreferrer")
                    self.assertCssClass(support_link_element, "btn")
                    self.assertCssClass(support_link_element, "btn-default")
                    self.assertEqual(
                        support_link_element.text(),
                        {
                            'en': "Support Pasporta Servo – Buy a cup of coffee for us!",
                            'eo': "Subtenu Pasportan Servon – Aĉetu por ni taseton da kafo!",
                        }[lang]
                    )

                    # This link is expected to be placed directly after the other
                    # social buttons.
                    self.assertCssClass(support_element.prev(), "social-links")

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_support_button_thanks(self):
        ProductReservationFactory.create(user=self.user, product_code='Donation')
        all_donations = (
            ProductReservationFactory._meta.model.objects
            .filter(user=self.user, product__code='Donation')
        )

        for count in [1, 2, 3, 4, 10]:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(donations_count=count, lang=lang)
                ):
                    all_donations.update(amount=count)
                    # Do not reuse the cached pages, load clean instances.
                    page = self.view_page.open(self, user=self.user)
                    support_element = page.pyquery(".social-support")
                    self.assertLength(support_element, 1)
                    # After a donation is registered, the support link is
                    # expected to have a "thank you" text.
                    self.assertEqual(
                        support_element.text(),
                        {
                            'en': "Thank you for your support!",
                            'eo': "Dankon por via subteno!",
                        }[lang]
                    )
                    # The support link is expected to include up to 3 "heart"
                    # elements, depending on the number of "base donations".
                    heart_elements = support_element.find(".fa-heart")
                    self.assertLength(heart_elements, min(count, 3))

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
                page = self.view_page.open(self, reuse_for_lang=lang)
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
                page = self.view_page.open(self, redirect_to='sit', reuse_for_lang=lang)
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
                page = self.view_page.open(self, redirect_to='', reuse_for_lang=lang)
                container_element = page.get_hero_content()
                self.assertLength(container_element.find("[role='search']"), 1)
                self.assertLength(container_element.find("a"), 0)

                # When the provided redirection target is insecure, the back
                # button is expected to be not shown.
                page = self.view_page.open(self, redirect_to='//fly', reuse_for_lang=lang)
                container_element = page.get_hero_content()
                self.assertLength(container_element.find("[role='search']"), 1)
                self.assertLength(container_element.find("a"), 0)


class GeneralViewTestsMixin(with_type_hint(BasicViewTests)):
    view_page: type[PageWithTitleHeadingTemplate]

    class TestParams(TypedDict):
        users: list[tuple[str, None | AbstractUser | UserFactory]]
        langs: list[str]

    @property
    def params_for_test(self) -> TestParams:
        return {
            'users': [
                ("anonymous", None),
                ("authenticated", self.user),
            ],
            'langs': ['en', 'eo'],
        }

    def test_page_title(self):
        # Verify the expected title of the page, which should be the same for
        # all users irrespective of the language.
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)
                    if isinstance(page.page_title, dict):
                        expected_title = page.page_title[lang]
                    else:
                        expected_title = page.page_title
                    self.assertEqual(page.get_heading_text(), expected_title)


class CollapseControlTestsMixin(with_type_hint(BasicViewTests)):
    def collapse_control_tests(
            self,
            control_element: PyQuery,
            target_element: PyQuery,
            initially_expanded: bool,
    ):
        target_id = target_element.attr("id")
        self.assertEqual(control_element.attr("role"), "button")
        self.assertEqual(control_element.attr("data-toggle"), "collapse")
        self.assertEqual(control_element.attr("data-target"), f"#{target_id}")
        self.assertEqual(control_element.attr("aria-controls"), target_id)
        self.assertCssClass(target_element, "collapse")
        if initially_expanded:
            self.assertEqual(control_element.attr("aria-expanded"), "true")
            self.assertCssClass(target_element, "in")
        else:
            self.assertEqual(control_element.attr("aria-expanded"), "false")
            self.assertFalse(target_element.has_class("in"))


class LanguageSwitcherTestsMixin(with_type_hint(BasicViewTests)):
    @staticmethod
    def setup_localized_about_pages():
        about_page_filter = Q(url__startswith='/pri-ni/')
        FlatPage.objects.filter(about_page_filter).delete()
        FlatPage.objects.create(
            url='/pri-ni/fa/', title="درباره ما",
            content="""
                زبان
                ----
                [FA] Localized Content
            """,
            template_name='pages/about_localized.html')
        FlatPage.objects.create(
            url='/pri-ni/az/', title="Haqqımızda", content="[AZ] Localized Content",
            template_name='pages/about_localized.html')
        FlatPage.objects.create(
            url='/pri-ni/vi/', title="Về chúng tôi", content="[VI] Localized Content",
            template_name='pages/about_localized.html')
        FlatPage.objects.create(
            url='/pri-ni/ga/', title="Fúinn", content="[GA] Localized Content",
            template_name='pages/about_localized.html')
        FlatPage.objects.create(
            url='/pri-ni/af/', title="Oor ons", content="[AF] Localized Content",
            template_name='pages/about_localized.html')
        about_page_ids = (
            FlatPage.objects.filter(about_page_filter).values_list('id', flat=True)
        )
        FlatPage.sites.through.objects.bulk_create([
            FlatPage.sites.through(site_id=settings.SITE_ID, flatpage_id=page_id)
            for page_id in about_page_ids
        ])

    @staticmethod
    def expected_language_labels() -> dict[str, dict[str | None, list[tuple[str, str]]]]:
        return {
            'en': {
                None: [
                    ('en', "English"),
                    ('af', "Afrikaans"),
                    ('az', "Azərbaycanca&ensp;•&ensp;Azerbaijani"),
                    ('fa', "فارسی&ensp;•&ensp;Persian"),
                    ('ga', "Gaeilge&ensp;•&ensp;Irish"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;Vietnamese"),
                ],
                'ko': [
                    ('en', "English&ensp;•&ensp;영어"),
                    ('af', "Afrikaans&ensp;•&ensp;아프리칸스어"),
                    ('az', "Azərbaycanca&ensp;•&ensp;아제르바이잔어"),
                    ('fa', "فارسی&ensp;•&ensp;페르시아어"),
                    ('ga', "Gaeilge&ensp;•&ensp;아일랜드어"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;베트남어"),
                ],
                'ga': [
                    ('en', "English&ensp;•&ensp;Béarla"),
                    ('af', "Afrikaans&ensp;•&ensp;Afracáinis"),
                    ('az', "Azərbaycanca&ensp;•&ensp;Asarbaiseáinis"),
                    ('fa', "فارسی&ensp;•&ensp;Peirsis"),
                    ('ga', "Gaeilge"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;Vítneamais"),
                ],
            },
            'eo': {
                None: [
                    ('eo', "Esperanto"),
                    ('af', "Afrikaans&ensp;•&ensp;Afrikansa"),
                    ('az', "Azərbaycanca&ensp;•&ensp;Azerbajĝana"),
                    ('fa', "فارسی&ensp;•&ensp;Persa"),
                    ('ga', "Gaeilge&ensp;•&ensp;Irlanda"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;Vjetnama"),
                ],
                'he': [
                    ('eo', "Esperanto&ensp;•&ensp;אספרנטו"),
                    ('af', "Afrikaans&ensp;•&ensp;אפריקאנס"),
                    ('az', "Azərbaycanca&ensp;•&ensp;אזרית"),
                    ('fa', "فارسی&ensp;•&ensp;פרסית"),
                    ('ga', "Gaeilge&ensp;•&ensp;אירית"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;וייטנאמית"),
                ],
                'ga': [
                    ('eo', "Esperanto"),
                    ('af', "Afrikaans&ensp;•&ensp;Afracáinis"),
                    ('az', "Azərbaycanca&ensp;•&ensp;Asarbaiseáinis"),
                    ('fa', "فارسی&ensp;•&ensp;Peirsis"),
                    ('ga', "Gaeilge"),
                    ('vi', "Tiếng Việt&ensp;•&ensp;Vítneamais"),
                ],
            },
        }

    def language_switcher_tests(
            self,
            user: AbstractUser | UserFactory | None, user_tag: str, lang: str,
            expected_label: str, expected_label_lang: Optional[str] = None,
            expected_bidi: Literal["ltr", "rtl"] = "ltr",
    ):
        for user_lang_pref in self.expected_language_labels()[lang]:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(user=user_tag, user_lang=user_lang_pref, lang=lang)
            ):
                accept = (
                    None if not user_lang_pref
                    else {'Accept-Language': user_lang_pref}
                )
                page = cast(
                    PageWithLanguageSwitcher,
                    self.view_page.open(self, user=user, extra_headers=accept)
                )
                # Verify the expected text and styling of the switcher.
                switch_label = page.get_lang_switcher_label()
                self.assertEqual(switch_label.text(), expected_label)
                self.assertEqual(switch_label.attr("lang"), expected_label_lang or lang)
                self.switch_label_styling_tests(page, switch_label)
                # The number of items in the drop-down menu is expected
                # to correlate with the number of localized "about" pages.
                switch_languages = page.get_lang_switcher_languages()
                expected_language_labels = (
                    self.expected_language_labels()[lang][user_lang_pref]
                )
                number_of_languages = len(expected_language_labels)
                start_count = 0 if page.is_localized_page() else 1
                self.assertLength(switch_languages, number_of_languages - start_count)
                # Each menu item is expected to be a link to the localized
                # page with its label being the language of that page.
                for i in range(number_of_languages - start_count):
                    language_element = switch_languages.eq(i)
                    test_data = cast(
                        tuple[str, str], expected_language_labels[i + start_count]
                    )
                    with self.subTest(switch_item=i, switch_item_code=test_data[0]):
                        self.switch_language_element_tests(
                            page, language_element, lang, user_lang_pref,
                            *test_data, expected_bidi,
                            uses_base_page_url=(i + start_count == 0),
                        )
                # The switcher is expected to have a default left-to-right
                # directionality.
                switch = page.get_lang_switcher()
                if switch.attr("dir"):
                    self.assertEqual(switch.attr("dir"), expected_bidi)
                if expected_bidi == "rtl":
                    self.assertIsNotNone(switch.attr("dir"))
                # The switcher is expected to be the first element on this
                # page, after the header.
                self.assertLength(switch.prev(), 0)

    def switch_label_styling_tests(
            self, page: PageWithLanguageSwitcher, switch_label: PyQuery,
    ):
        # The language switcher label is expected to by styled as a button and
        # have the secondary brand color.
        switch_label_container = switch_label.parent()
        self.assertCssClass(switch_label_container, "btn")
        self.assertCssClass(switch_label_container, "btn-default")
        self.assertCssClass(switch_label_container, "text-brand-aux")

    def switch_language_element_tests(
            self,
            page: PageWithLanguageSwitcher, language_element: PyQuery,
            lang: str, user_lang_pref: str | None,
            expected_code: str, expected_label: str, expected_bidi: Literal["ltr", "rtl"],
            uses_base_page_url: bool,
    ):
        # Verify the expected language label.
        self.assertHTMLEqual(
            # Work around PyQuery's incorrect handling of <bdi>.
            # https://github.com/gawel/pyquery/issues/253
            cast(
                str,
                language_element.text(block_symbol="", squash_space=False)
            ).strip(),
            expected_label)
        # The language element is expected to be an <a> directly linking to the
        # localized content page.
        self.assertTrue(language_element.is_("a"))
        self.assertEqual(
            language_element.attr("href"),
            f'/pri-ni/{expected_code}/' if not uses_base_page_url
            else page.base_url_for_localized_page)
        # The first item in the language label (the native name) is expected to
        # appear bold.
        language_name_element = language_element.children().eq(0)
        self.assertTrue(language_name_element.is_("b"))
        # The native language name should be tagged with its language code, for
        # assistive technologies to properly read it.
        self.assertEqual(language_name_element.attr("lang"), expected_code)
        # The language name is expected to be highlighted if it is the user's
        # preferred language on the base (non-localized) content page, or if it
        # matches the localized page's locale.
        if not page.is_localized_page() and user_lang_pref == expected_code:
            self.assertCssClass(language_name_element, "text-primary")
        elif page.is_localized_page() and page.locale == expected_code:
            self.assertCssClass(language_name_element, "text-primary")
        else:
            self.assertFalse(language_name_element.has_class("text-primary"))
        # The second item in the language label (the translated name), if it
        # appears, should be tagged with the user's language code, if available,
        # otherwise with the system language code.
        if "•" in expected_label:
            language_name_element = language_element.children().eq(-1)
            self.assertEqual(language_name_element.attr("lang"), user_lang_pref or lang)
        # The language element is expected to be contained in an element with
        # ARIA role of 'menu item', whose parent in turn is expected to have
        # the ARIA 'menu' role.
        self.assertEqual(language_element.parent().attr("role"), "menuitem")
        switch_languages_container = language_element.parent().parent()
        self.assertEqual(switch_languages_container.attr("role"), "menu")
        match expected_bidi:
            case "ltr":
                self.assertCssClass(switch_languages_container, "dropdown-menu-right")
            case "rtl":
                self.assertCssClass(switch_languages_container, "dropdown-menu-left")
        # Verify that it is possible to navigate to the correct localized page;
        # correctness is asserted using the content of the page.
        response = page.response.goto(language_element.attr("href"), status='*')
        if not uses_base_page_url:
            self.assertContains(
                response,
                f"[{expected_code.upper()}] Localized Content",
                status_code=200,
            )
        else:
            self.assertNotContains(
                response, "Localized Content", status_code=200,
            )


@tag('views', 'views-general', 'views-about')
class AboutViewTests(GeneralViewTestsMixin, LanguageSwitcherTestsMixin, BasicViewTests):
    view_page: type[AboutPage] = AboutPage

    def test_attribution(self):
        # The "about us" page is expected to have a section (or sections) with
        # an author rights attribution text.
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)
                    attribution_elements = page.get_attribution()
                    self.assertGreaterEqual(len(attribution_elements), 1)
                    # The attribution section itself or its container are expected
                    # to be styled as a help block (lighter and smaller text).
                    for attrib_element in attribution_elements.items():
                        external_link_elements = attrib_element.find("a")
                        self.assertCssClass(
                            attrib_element.extend(attrib_element.parent()),
                            "help-block"
                        )
                        # Each link within the attribution section is expected to
                        # be properly marked as external.
                        for link_element in external_link_elements.items():
                            with self.subTest(link=link_element.attr("href")):
                                self.assertEqual(
                                    link_element.attr("rel"),
                                    "external noreferrer"
                                )

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_language_switcher(self):
        self.setup_localized_about_pages()
        expected_label = {
            'en': "In another language",
            'eo': "En alia lingvo",
        }
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                self.language_switcher_tests(user, user_tag, lang, expected_label[lang])

    def test_statistics_caching(self):
        # The "about us" page is expected to cache the statistics shown about
        # the current number of hosts.
        page_fragment_key = make_template_fragment_key('hosting-service-statistics')
        for user_tag, user in self.params_for_test['users']:
            with self.subTest(user=user_tag):
                cache.delete(page_fragment_key)
                # Load the root page first, so that session management, loading of site
                # configuration, etc., do not pollute the results.
                self.app.get('/', user=user)
                # Do not reuse the cached pages, load clean instances.
                with CaptureQueriesContext(connections[DEFAULT_DB_ALIAS]) as ctx:
                    self.view_page.open(self, user=user)
                number_of_queries_on_first_load = len(ctx.captured_queries)
                # Loading the "about us" page again is expected to reuse cached results
                # and not perform the 3 queries for number of hosts, of countries, and
                # of cities.
                with self.assertNumQueries(number_of_queries_on_first_load - 3):
                    self.view_page.open(self, user=user)

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_statistics(self):
        # TODO
        pass


@tag('views', 'views-general', 'views-about')
class AboutInIrishViewTests(LanguageSwitcherTestsMixin, BasicViewTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class FuinnPage(AboutPage):
            view_class = None
            explicit_url = {
                'en': '/pri-ni/ga/',
                'eo': '/pri-ni/ga/',
            }
            base_url_for_localized_page = reverse_lazy('about')
            template = 'pages/about_localized.html'
            title = {
                'en': "Fúinn : Pasporta Servo",
                'eo': "Fúinn : Pasporta Servo",
            }

            @classproperty
            def url(cls):
                return cls.explicit_url[settings.LANGUAGE_CODE]

            def is_localized_page(self):
                return True

            @property
            def locale(self):
                return 'ga'

        cls.view_page = FuinnPage

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.setup_localized_about_pages()

    def test_language_switcher(self):
        expected_label = {
            'en': "In another language",
            'eo': "En alia lingvo",
        }
        for lang, expected_label_text in expected_label.items():
            self.language_switcher_tests(
                None, "anonymous", lang, expected_label_text,
            )


@tag('views', 'views-general', 'views-about')
class AboutInFarsiViewTests(LanguageSwitcherTestsMixin, BasicViewTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class DerbarhPage(AboutPage):
            view_class = None
            explicit_url = {
                'en': '/pri-ni/fa/',
                'eo': '/pri-ni/fa/',
            }
            base_url_for_localized_page = reverse_lazy('about')
            template = 'pages/about_localized.html'
            title = {
                'en': "درباره ما : Pasporta Servo",
                'eo': "درباره ما : Pasporta Servo",
            }

            @classproperty
            def url(cls):
                return cls.explicit_url[settings.LANGUAGE_CODE]

            def is_localized_page(self):
                return True

            @property
            def locale(self):
                return 'fa'

        cls.view_page = DerbarhPage

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.setup_localized_about_pages()

    def test_language_switcher(self):
        expected_label = {
            'en': "زبان",
            'eo': "زبان",
        }
        for lang, expected_label_text in expected_label.items():
            self.language_switcher_tests(
                None, "anonymous", lang, expected_label_text, 'fa', "rtl",
            )


@tag('views', 'views-general')
class FAQViewTests(GeneralViewTestsMixin, BasicViewTests):
    view_page: type[FAQPage] = FAQPage

    def test_sections_structure(self):
        expected_texts = [
            "Pri kaj post la registriĝo.",
            "Kial mi fariĝu gastiganto?",
            "Se vi estas gasto…",
            "Pasporta Servo – libra versio.",
        ]

        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, reuse_for_lang=lang)
                    headings = page.get_section_headings()
                    # The FAQ page is expected to have 4 main sections.
                    self.assertLength(headings, 4)
                    # Each section is expected to have a heading with `id` and `name`
                    # attributes (for hot-linking) and the pre-defined text.
                    for i, heading_element in enumerate(headings.items()):
                        with self.subTest(heading=heading_element):
                            self.assertEqual(heading_element.text(), expected_texts[i])
                            self.assertNotEqual(heading_element.attr("id"), "")
                            self.assertIsNotNone(heading_element.attr("name"))


@tag('views', 'views-general')
class TermsAndConditionsViewTests(GeneralViewTestsMixin, BasicViewTests):
    view_page: type[TCPage] = TCPage
    terms_page_filter = Q(url='/terms-conditions/')

    def test_terms_structure(self):
        faker = Faker(locale='la')
        terms_count = faker.pyint(3, 10)
        FlatPage.objects.filter(self.terms_page_filter).update_or_create({
            'content': "\n\n".join(
                faker.sentence(nb_words=12) for _ in range(terms_count)
            ),
        })
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    items = page.get_terms_items()
                    self.assertLength(items, terms_count)
                    for terms_item in items.items():
                        self.assertEqual(terms_item[0].tag, 'blockquote')
                        self.assertNotEqual(terms_item.text(), "")

    def test_terms_encoding(self):
        faker = Faker(locale='la')
        FlatPage.objects.filter(self.terms_page_filter).update_or_create({
            'content': "\r\n\r\n".join([
                f"{faker.sentence()} <em>{faker.sentence()}</em> {faker.sentence()}",
                f"<!-- {faker.sentence()} --> \t <u>{faker.word()}</u>"
                + f"<span>{faker.word()}</span>",
            ]),
        })
        expected_nodes = [
            [str, (HtmlElement, 'em'), str],
            [str, HtmlComment, str, (HtmlElement, 'u'), (HtmlElement, 'span'), str]
        ]
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    items = page.get_terms_items()
                    self.assertLength(items, 2)
                    for i, item in enumerate(items):
                        with self.subTest(term=i + 1):
                            item_child_nodes = item.xpath('child::node()')
                            self.assertLength(item_child_nodes, len(expected_nodes[i]))
                            for j, child_node in enumerate(item_child_nodes):
                                if isinstance(expected_nodes[i][j], tuple):
                                    expected_type, expected_tag = expected_nodes[i][j]
                                else:
                                    expected_type = expected_nodes[i][j]
                                    expected_tag = None
                                with self.subTest(
                                        node=child_node.__class__.__name__,
                                        position=j + 1,
                                ):
                                    self.assertIsInstance(child_node, expected_type)
                                    if expected_tag is not None:
                                        self.assertEqual(child_node.tag, expected_tag)

    def test_missing_content(self):
        FlatPage.objects.filter(self.terms_page_filter).delete()
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user, status=404)
                    heading_elements = page.get_404_headings()
                    self.assertLength(heading_elements, 2)
                    self.assertEqual(
                        heading_elements.eq(1).text(),
                        {'en': "Page not found", 'eo': "Paĝo ne trovita"}[lang]
                    )

    def test_empty_content(self):
        dummy_content = " \t" * 3 + "\n" * 3 + "\f" * 2 + "\r\n" * 2 + "  " * 5
        FlatPage.objects.filter(self.terms_page_filter).update_or_create({
            'content': dummy_content,
        })
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    # When the T&C flatpage does not have any content, no terms
                    # are expected to be shown on the page visible to the users.
                    self.assertLength(page.get_terms_items(), 0)
                    # The page's title is still expected to be displayed.
                    if isinstance(page.page_title, dict):
                        expected_title = page.page_title[lang]
                    else:
                        expected_title = page.page_title
                    self.assertEqual(page.get_heading_text(), expected_title)


@tag('views', 'views-general')
class PrivacyViewTests(GeneralViewTestsMixin, CollapseControlTestsMixin, BasicViewTests):
    view_page: type[PrivacyPage] = PrivacyPage

    def test_policy_display(self):
        # The view is expected to display the latest policy already in effect
        # (that is, already binding), otherwise the available future policy.
        Policy.objects.all().delete()
        policy = PolicyFactory(version='XYZ', from_future_date=True, with_summary=False)
        for current_policy in [False, True]:
            if current_policy:
                policy = PolicyFactory(
                    version='ABCD', from_past_date=True, with_summary=False)
            for user_tag, user in self.params_for_test['users']:
                for lang in self.params_for_test['langs']:
                    with (
                        override_settings(LANGUAGE_CODE=lang),
                        self.subTest(future_policy=not current_policy,
                                     user=user_tag, lang=lang)
                    ):
                        page = self.view_page.open(self, user=user)
                        # Verify that the expected policy is displayed on the page.
                        # The policy should be rendered as HTML.
                        if not current_policy:
                            self.assertContains(page.response, "Policy XYZ")
                            self.assertContains(
                                page.response, "<p>Policy XYZ</p>", html=True)
                        else:
                            self.assertContains(page.response, "Policy ABCD")
                            self.assertContains(
                                page.response, "<p>Policy ABCD</p>", html=True)
                            self.assertNotContains(page.response, "Policy XYZ")
                        # The page is expected to display the date from which the
                        # policy is in effect.
                        localized_effective_date = localize(policy.effective_date)
                        with translation.override('eo'):
                            esperanto_effective_date = localize(policy.effective_date)
                        effective_element = page.get_effective_date()
                        self.assertLength(effective_element, 1)
                        self.assertEqual(
                            effective_element.text(),
                            {
                                'en': f"Effective from {localized_effective_date}",
                                'eo': f"En efiko ekde {localized_effective_date}",
                            }[lang]
                        )
                        # The page is expected to include a note about policy validity.
                        effective_element = page.get_validity_note()
                        self.assertLength(effective_element, 1)
                        self.assertEqual(effective_element.attr("role"), "note")
                        self.assertEqual(
                            effective_element.text(),
                            f"Tiu ĉi politiko estas en efiko ekde {esperanto_effective_date}."
                        )
                        # The note should be the last element of the page -- after the
                        # policy and before the footer.
                        effective_element_container = effective_element.parents("blockquote")
                        self.assertLength(effective_element_container, 1)
                        self.assertLength(effective_element_container.next(), 0)

    def test_policy_summary_display(self):
        # The view is expected to display no summary if it is not defined or empty.
        Policy.objects.all().delete()
        PolicyFactory(with_summary=False)
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    self.assertLength(page.get_summary(), 0)

        # The view is expected to display the summary of the shown policy, when
        # defined. The summary should be contained in an interactive container,
        # and rendered as HTML.
        Policy.objects.all().delete()
        policy = PolicyFactory(with_summary=True)
        policy.changes_summary += "<br />\n" + "<em>\n\t Sentinel Element \n\t</em>"
        policy.save()
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    summary_element = page.get_summary()
                    self.assertLength(summary_element, 1)
                    self.assertCssClass(summary_element, "panel")
                    self.assertCssClass(summary_element, "panel-info")
                    # The element containing the summary is expected to be collapsible
                    # and folded by default.
                    panel_heading_element = summary_element.children(".panel-heading")
                    panel_body_element = summary_element.children(f"#{page.get_summary_id()}")
                    self.assertLength(panel_heading_element, 1)
                    self.collapse_control_tests(
                        panel_heading_element, panel_body_element, False)
                    self.assertEqual(
                        panel_heading_element.text(),
                        {
                            'en': "Summary of the changes",
                            'eo': "Resumo de la ŝanĝoj",
                        }[lang]
                    )
                    # Verify that the content is properly labeled.
                    self.assertEqual(
                        panel_body_element.attr("aria-labelledby"),
                        panel_heading_element.attr("id"))
                    # Verify that the content is not HTML-encoded on output.
                    self.assertNotEqual(panel_body_element.text(), "")
                    self.assertInHTML("<em>Sentinel Element</em>", panel_body_element.html())

    def test_missing_policy(self):
        # When no privacy policies are defined at all, the view is expected
        # to raise a RuntimeError.
        Policy.objects.all().delete()
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    with self.assertRaisesMessage(
                            RuntimeError,
                            "Service misconfigured: No privacy policy is defined."
                    ):
                        self.view_page.open(self, user=user)

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_list_of_policies(self):
        # The view is expected to include no drop-down for selecting other
        # policies if only a single policy is defined.
        Policy.objects.all().delete()
        PolicyFactory(with_summary=False)
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    self.assertLength(page.get_policy_switcher(), 0)

        # The view is expected to have a drop-down for selecting other policies
        # to review, and to enable navigation to these policies.
        PolicyFactory.create_batch(
            3, from_past_date=True, with_summary=False, requires_consent=False)
        PolicyFactory.create_batch(
            2, from_future_date=True, with_summary=False)
        # The list of policies is expected to be sorted in descending order
        # by date of validity (newest policy on top, oldest on bottom).
        expected_policies = (
            Policy.objects
            .order_by('-effective_date')
            .values('version', 'effective_date')
        )
        expected_label = {
            'en': "Other versions",
            'eo': "Aliaj versioj",
        }
        for user_tag, user in self.params_for_test['users']:
            for lang in self.params_for_test['langs']:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    page = self.view_page.open(self, user=user)
                    switch_elements = page.get_policy_switcher()
                    self.assertLength(switch_elements, 2)

                    # Verify that all policies are included in the interactive drop-
                    # down (JavaScript) and can be accessed by clicking the items in
                    # the list.
                    js_switch = switch_elements.eq(0)
                    # The two strings representing the outer HTML of the element are
                    # expected to be exactly the same if it is the same HTML element;
                    # therefore, there is no need to test for HTML equality.
                    self.assertEqual(
                        js_switch.prev_all("*:not(p.clearfix)").eq(-1).outer_html(),
                        page.get_effective_date().outer_html()
                    )
                    self.interactive_switch_tests(
                        page, expected_policies, expected_label[lang],
                    )

                    # Verify that all policies are included in the static drop-down
                    # (simple <select> not requiring JavaScript) and can be accessed
                    # by selecting an item and submitting the form.
                    static_switch = switch_elements.eq(1)
                    self.assertTrue(static_switch.parent().is_("noscript"))
                    self.static_switch_tests(
                        page, lang, expected_policies, expected_label[lang],
                    )

    def interactive_switch_tests(
            self,
            page: PrivacyPage, expected_policies, expected_label: str,
    ):
        # Verify the expected text and styling of the switcher.
        self.interactive_switch_label_styling_tests(page, expected_label)

        # The number of items in the drop-down menu is expected
        # to correlate with the number of available policies.
        switch_items = page.get_policy_switcher_items(js=True)
        self.assertLength(switch_items, len(expected_policies))

        # Each menu item is expected to be a link to the specific
        # policy version with its label being the effective date
        # of that policy.
        for i in range(len(expected_policies)):
            switch_item_element = switch_items.eq(i)
            expected_item_label = localize(expected_policies[i]['effective_date'])
            expected_item_url = reverse(
                'privacy_policy_version',
                kwargs={'policy_version': expected_policies[i]['version']})
            with self.subTest(switch_item=i + 1):
                self.interactive_switch_item_tests(
                    page, switch_item_element, expected_policies[i]['effective_date'],
                    expected_item_label, expected_item_url,
                )

    def interactive_switch_label_styling_tests(
            self,
            page: PrivacyPage, expected_label: str,
    ):
        switch_label = page.get_policy_swither_label(js=True)
        self.assertEqual(switch_label.text(), expected_label)
        # The switcher label is expected to by styled as a button
        # and have the secondary brand color.
        switch_label_container = switch_label.parent()
        self.assertCssClass(switch_label_container, "btn")
        self.assertCssClass(switch_label_container, "btn-default")
        self.assertCssClass(switch_label_container, "text-brand-aux")

    def interactive_switch_item_tests(
            self,
            page: PrivacyPage, policy_element: PyQuery, policy_date: date,
            expected_label: str, expected_url: str,
    ):
        # Verify the expected label.
        self.assertEqual(policy_element.text(), expected_label)
        # The switch element is expected to be an <a> directly linking to the
        # policy page.
        self.assertTrue(policy_element.is_("a"))
        self.assertEqual(policy_element.attr("href"), expected_url)
        # The switch element is expected to be contained in an element with
        # ARIA role of 'menu item', whose parent in turn is expected to have
        # the ARIA 'menu' role. The menu item container is expected to be
        # marked as active if the switch item corresponds to the policy shown
        # on the page.
        policy_element_container = policy_element.parent()
        self.assertEqual(policy_element_container.attr("role"), "menuitem")
        self.assertCssClass(policy_element_container, "text-center")
        localized_policy_date = localize(policy_date)
        if page.get_effective_date().text().endswith(localized_policy_date):
            self.assertCssClass(policy_element_container, "active")
        else:
            self.assertFalse(policy_element_container.has_class("active"))
        self.assertEqual(policy_element_container.parent().attr("role"), "menu")

        # Verify that it is possible to navigate to the correct policy page;
        # correctness is asserted using the content of the page.
        new_page = PrivacyPage.wrap_response(
            self, page.response.goto(policy_element.attr("href"), status='*'))
        effective_element = new_page.get_validity_note()
        with translation.override('eo'):
            esperanto_policy_date = localize(policy_date)
        self.assertEqual(
            effective_element.text(),
            f"Tiu ĉi politiko estas en efiko ekde {esperanto_policy_date}."
        )

    def static_switch_tests(
            self,
            page: PrivacyPage, current_lang: str, expected_policies, expected_label: str,
    ):
        # Verify the expected text and styling of the switcher's label.
        switch_label = page.get_policy_swither_label(js=False)
        self.assertEqual(switch_label.text(), expected_label)
        # The switcher label is expected to by visible only to screen readers.
        self.assertCssClass(switch_label, "sr-only")

        # The number of items in the <select> element is expected to correlate
        # with the number of available policies.
        switch_items = page.get_policy_switcher_items(js=False)
        self.assertLength(switch_items, len(expected_policies) + 2)
        # The <select> element is expected to be described by the label.
        self.assertEqual(switch_label.attr("for"), switch_items.parent().attr("id"))

        # Verify the expected test and styling of the submit button for
        # the switcher form.
        submit_button = page.get_policy_switcher_submit(js=False)
        self.assertEqual(
            submit_button.attr("value"),
            {'en': "Show", 'eo': "Montri"}[current_lang]
        )
        self.assertEqual(submit_button.text(), "")
        self.assertCssClass(submit_button, "btn")
        self.assertCssClass(submit_button, "btn-primary")
        self.assertLength(submit_button.parents("form"), 1)

        form_element = switch_items.parents("form")
        self.assertIsNotNone(form_element.attr("id"))
        form = cast(dict[int | str, HtmlForm], page.response.forms)[
            cast(str, form_element.attr("id"))
        ]
        # The first two items of the <select> are expected to be a label
        # and a separator, both pointing to no specific policy.
        skip = 0
        with self.subTest(switch_item=skip + 1):
            self.static_switch_item_tests(
                page, form, current_lang, switch_items.eq(skip), None,
                expected_label, "", is_list_label=True,
            )
        skip += 1
        with self.subTest(switch_item=skip + 1):
            self.static_switch_item_tests(
                page, form, current_lang, switch_items.eq(skip), None,
                "---------", "", is_list_label=False,
            )
        skip += 1
        # Each other item of the <select> is expected to point to a specific
        # policy version with its text being the effective date of that policy.
        for i in range(len(expected_policies)):
            switch_item_element = switch_items.eq(i + skip)
            expected_item_text = localize(expected_policies[i]['effective_date'])
            expected_item_value = expected_policies[i]['version']
            with self.subTest(switch_item=i + skip + 1):
                self.static_switch_item_tests(
                    page, form, current_lang, switch_item_element,
                    expected_policies[i]['effective_date'],
                    expected_item_text, expected_item_value,
                )
        # Submitting an unexpected / invalid value as the policy version is
        # expected to be handled gracefully and result in a "Not Found" page.
        form[switch_items.parent().attr("name")].force_value("NotExistent")
        response = form.submit(status='*')
        self.assertEqual(response.status_code, 404)

    def static_switch_item_tests(
            self,
            page: PrivacyPage, form: HtmlForm, current_lang: str,
            policy_element: PyQuery, policy_date: date | None,
            expected_text: str, expected_value: str, is_list_label: bool = False,
    ):
        # Verify the expected text and value of the <option>.
        self.assertEqual(policy_element.text(), expected_text)
        self.assertEqual(policy_element.attr("value"), expected_value)
        if is_list_label:
            self.assertIsNotNone(policy_element.attr("selected"))
        else:
            self.assertIsNone(policy_element.attr("selected"))
        localized_policy_date = localize(policy_date)
        if (
                policy_date is not None
                and page.get_effective_date().text().endswith(localized_policy_date)
        ):
            self.assertIsNotNone(policy_element.attr("disabled"))
        else:
            self.assertIsNone(policy_element.attr("disabled"))

        # Verify that it is possible to navigate to the correct policy page;
        # correctness is asserted using the content of the page and it title.
        form.select(policy_element.parent().attr("name"), expected_value)
        new_page = PrivacyPage.wrap_response(self, form.submit(status='*'))
        self.assertEqual(new_page.response.status_code, 200)
        effective_element = new_page.get_validity_note()
        if policy_date is not None:
            with translation.override('eo'):
                esperanto_policy_date = localize(policy_date)
            self.assertEqual(
                effective_element.text(),
                f"Tiu ĉi politiko estas en efiko ekde {esperanto_policy_date}."
            )
            self.assertStartsWith(
                new_page.pyquery("title").text(),
                "Politiko pri privateco (ekde "
            )
        else:
            # When policy version is not given, navigation is expected to
            # occur to the most up-to-date already-valid policy.
            self.assertEqual(
                new_page.pyquery("title").text(),
                PrivacyPage.title[current_lang]
            )

    # TODO: Test specific policy view (by version).
