from django.conf import settings
from django.test import override_settings, tag
from django.utils.html import format_html

from django_webtest import WebTest
from factory import Faker

from hosting.gravatar import email_to_gravatar
from hosting.utils import value_without_invalid_marker

from ..assertions import AdditionalAsserts
from ..factories import ProfileFactory, ProfileSansAccountFactory, UserFactory
from .test_managers import TrackingManagersTests


@tag('models', 'profile')
class ProfileModelTests(AdditionalAsserts, TrackingManagersTests, WebTest):
    factory = ProfileFactory

    @classmethod
    def setUpTestData(cls):
        cls.template_first_name = '<span class="first-name">{name}</span>'
        cls.template_last_name = '<span class="last-name">{name}</span>'
        cls.template_username = '<span class="profile-noname">{name}</span>'
        cls.template_joiner = '&ensp;'

        cls.basic_profile = ProfileFactory(first_name="Aaa", last_name="Bbb")

    def test_field_max_lengths(self):
        profile = self.basic_profile
        self.assertEqual(profile._meta.get_field('title').max_length, 5)
        self.assertEqual(profile._meta.get_field('first_name').max_length, 255)
        self.assertEqual(profile._meta.get_field('last_name').max_length, 255)
        self.assertEqual(profile._meta.get_field('pronoun').max_length, 10)

    def test_name(self):
        # A profile with name "Aa" is expected to be "Aa".
        profile = ProfileFactory.build(first_name="Aa", last_name="Bb")
        self.assertEqual(profile.name, "Aa")
        # A profile with name "Aa", names inversed, is expected to be "Aa".
        profile = ProfileFactory.build(first_name="Aa", last_name="Bb", names_inversed=True)
        self.assertEqual(profile.name, "Aa")
        # A profile with name "  Aa  " is expected to be "Aa".
        profile = ProfileFactory.build(first_name="  Aa  ", last_name="Bb")
        self.assertEqual(profile.name, "Aa")
        # A profile with name "" is expected to be "".
        profile = ProfileFactory.build(first_name="", last_name="Bb")
        self.assertEqual(profile.name, "")
        # A profile with name "  " is expected to be "".
        profile = ProfileFactory.build(first_name="  ", last_name="Bb")
        self.assertEqual(profile.name, "")

    def test_fullname(self):
        # Normal profile with both names is expected to be "Aa Bb".
        profile = ProfileFactory.build()
        self.assertEqual(profile.full_name, '{} {}'.format(profile.first_name, profile.last_name))

        # Normal profile with both names, inversed, is expected to be "Bb Aa".
        profile = ProfileFactory.build(names_inversed=True)
        self.assertEqual(profile.full_name, '{} {}'.format(profile.last_name, profile.first_name))

        # A profile with only last name is expected to be "Bb".
        profile = ProfileFactory.build(first_name="")
        self.assertEqual(profile.full_name, profile.last_name)
        # A profile with only last name, names inversed, is expected to be "Bb".
        profile = ProfileFactory.build(first_name="", names_inversed=True)
        self.assertEqual(profile.full_name, profile.last_name)

        # A profile with only first name is expected to be "Aa".
        profile = ProfileFactory.build(last_name="")
        self.assertEqual(profile.full_name, profile.first_name)
        # A profile with only first name, names inversed, is expected to be "Aa".
        profile = ProfileFactory.build(last_name="", names_inversed=True)
        self.assertEqual(profile.full_name, profile.first_name)

        # A profile with no names provided is expected to have empty output.
        profile = ProfileFactory.build(first_name="", last_name="")
        self.assertEqual(profile.full_name, "")
        # A profile with no names provided (inversed) is expected to have empty output.
        profile = ProfileFactory.build(first_name="", last_name="", names_inversed=True)
        self.assertEqual(profile.full_name, "")

    def test_profile_fullname_template(self):
        # Normal profile with both names is expected to be "Aa Bb".
        profile = ProfileFactory()
        self.assertEqual(profile.get_fullname_display(), self.template_joiner.join([
            format_html(self.template_first_name, name=profile.first_name),
            format_html(self.template_last_name, name=profile.last_name),
        ]))

        # Normal profile with both names, inversed, is expected to be "Bb Aa".
        profile = ProfileFactory(names_inversed=True)
        self.assertEqual(profile.get_fullname_display(), self.template_joiner.join([
            format_html(self.template_last_name, name=profile.last_name),
            format_html(self.template_first_name, name=profile.first_name),
        ]))

        # A profile with only last name is expected to be "Bb".
        profile = ProfileFactory(first_name="")
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_last_name, name=profile.last_name)
        ))
        # A profile with only last name, names inversed, is expected to be "Bb".
        profile = ProfileFactory(first_name="", names_inversed=True)
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_last_name, name=profile.last_name)
        ))

        # A profile with only first name is expected to be "Aa".
        profile = ProfileFactory(last_name="")
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_first_name, name=profile.first_name)
        ))
        # A profile with only first name, names inversed, is expected to be "Aa".
        profile = ProfileFactory(last_name="", names_inversed=True)
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_first_name, name=profile.first_name)
        ))

        # A profile with no names provided is expected to be "Uu".
        profile = ProfileFactory(first_name="", last_name="")
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_username, name=profile.user.username.title())
        ))
        # A profile with no names provided, names inversed, is expected to be "Uu".
        profile = ProfileFactory(first_name="", last_name="", names_inversed=True)
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_username, name=profile.user.username.title())
        ))
        # A profile with no user account and no names provided is expected to have empty output.
        profile = ProfileSansAccountFactory(first_name="", last_name="")
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_username, name=" ")
        ))
        # A profile with no user account and no names provided (inversed) is expected to have empty output.
        profile = ProfileSansAccountFactory(first_name="", last_name="", names_inversed=True)
        self.assertEqual(profile.get_fullname_display(), (
            format_html(self.template_username, name=" ")
        ))
        # When 'always', a profile with no user and no names provided is expected to have output of a dash.
        profile = ProfileSansAccountFactory(first_name="", last_name="")
        self.assertEqual(profile.get_fullname_always_display(), (
            format_html(self.template_username, name="--")
        ))
        # When 'always', a profile with no user, no names provided (inversed) is expected to have output of a dash.
        profile = ProfileSansAccountFactory(first_name="", last_name="", names_inversed=True)
        self.assertEqual(profile.get_fullname_always_display(), (
            format_html(self.template_username, name="--")
        ))

    def test_age(self):
        profile = ProfileFactory.build(birth_date=None)
        self.assertRaises(TypeError, lambda: profile.age)
        profile = ProfileFactory.build(birth_date=Faker('date_this_year', before_today=True, after_today=False))
        self.assertEqual(profile.age, 0)
        profile = ProfileFactory.build(birth_date=Faker('date_this_year', before_today=False, after_today=True))
        self.assertEqual(profile.age, 0)
        profile = ProfileFactory.build(birth_date=Faker('date_between', start_date='-725d', end_date='-366d'))
        self.assertEqual(profile.age, 1)
        profile = ProfileFactory.build(birth_date=Faker('date_between', start_date='+366d', end_date='+725d'))
        self.assertEqual(profile.age, -1)
        profile = ProfileFactory.build(birth_date=Faker('date_between', start_date='-6935d', end_date='-6575d'))
        self.assertEqual(profile.age, 18)

        profile = ProfileFactory.build(birth_date=None, death_date=Faker('date_this_year'))
        self.assertRaises(TypeError, lambda: profile.age)
        profile = ProfileFactory.build(
            birth_date=Faker('date_between', start_date='-2000d', end_date='-1825d'),
            death_date=Faker('date_between', start_date='-360d', end_date='-185d'))
        self.assertEqual(profile.age, 4)
        profile = ProfileFactory.build(
            birth_date=Faker('date_between', start_date='-2000d', end_date='-1825d'),
            death_date=Faker('date_between', start_date='+370d', end_date='+545d'))
        self.assertEqual(profile.age, 6)

    def test_avatar_url(self):
        # A normal profile is expected to be gravatar url for email.
        profile = ProfileFactory()
        self.assertEqual(
            profile.avatar_url,
            email_to_gravatar(profile.user.email, settings.DEFAULT_AVATAR_URL)
        )
        # A normal profile with invalid email is expected to be gravatar url for email.
        user = UserFactory(invalid_email=True)
        profile = ProfileFactory(user=user)
        self.assertEqual(
            profile.avatar_url,
            email_to_gravatar(value_without_invalid_marker(profile.user.email), settings.DEFAULT_AVATAR_URL)
        )

        # A profile with no user account is expected to be gravatar url for fake family member email.
        profile = ProfileSansAccountFactory()
        self.assertEqual(
            profile.avatar_url,
            email_to_gravatar("family.member@pasportaservo.org", settings.DEFAULT_AVATAR_URL)
        )

    def test_icon(self):
        profile = ProfileFactory.build()
        self.assertSurrounding(profile.icon, "<span ", "></span>")
        self.assertIn(" title=", profile.icon)

    def test_str(self):
        # Normal profile with both names is expected to be "Aa Bb".
        profile = ProfileFactory()
        self.assertEqual(str(profile), '{} {}'.format(profile.first_name, profile.last_name))

        # A profile with no names provided is expected to be "Anonymous (uu)".
        profile = ProfileFactory(first_name="", last_name="")
        self.assertEqual(str(profile), '{} ({})'.format(str(profile.INCOGNITO), profile.user.username))

        # A profile with no user account and both names is expected to be "Aa Bb".
        profile = ProfileSansAccountFactory()
        self.assertEqual(str(profile), '{} {}'.format(profile.first_name, profile.last_name))
        # A profile with no user account and no names provided is expected to have output of a dash.
        profile = ProfileSansAccountFactory(first_name="", last_name="")
        self.assertEqual(str(profile), "--")

    def test_repr(self):
        profile = ProfileFactory()
        self.assertSurrounding(repr(profile), f"<Profile #{profile.pk}:", ">")

    def test_rawdisplay(self):
        # Raw string for profile with a birth date is expected to include the birth year.
        profile = ProfileFactory()
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} ({profile.birth_date.year})")
        profile = ProfileFactory(first_name="", last_name="")
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} ({profile.birth_date.year})")
        profile = ProfileSansAccountFactory()
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} ({profile.birth_date.year})")

        # Raw string for profile without a birth date is expected to include a question mark.
        profile = ProfileFactory(birth_date=None)
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} (?)")
        profile = ProfileFactory(first_name="", last_name="", birth_date=None)
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} (?)")
        profile = ProfileSansAccountFactory(birth_date=None)
        self.assertEqual(profile.rawdisplay(), f"{str(profile)} (?)")

    def test_lt(self):
        p1 = ProfileFactory(first_name="Aa", last_name="Yy")
        p2 = ProfileFactory(first_name="Aa", last_name="Zz")
        p3 = ProfileFactory(first_name="Bb", last_name="Yy")
        p4 = ProfileFactory(first_name="Bb", last_name="Zz")
        self.assertTrue(p1 < p2)
        self.assertTrue(p1 < p3)
        self.assertTrue(p1 < p4)
        self.assertFalse(p2 < p1)
        self.assertFalse(p2 < p3)
        self.assertTrue(p2 < p4)
        self.assertFalse(p3 < p1)
        self.assertTrue(p3 < p2)
        self.assertTrue(p3 < p4)
        self.assertFalse(p4 < p1)
        self.assertFalse(p4 < p2)
        self.assertFalse(p4 < p3)

    def test_get_basic_data(self):
        # The get_basic_data function is expected to be a class (only) method.
        self.assertRaises(AttributeError, lambda: self.basic_profile.get_basic_data(pk=1))

        # The database query is expected to return sufficient data to generate URLs.
        with self.assertNumQueries(1):
            p = self.basic_profile.__class__.get_basic_data(user=self.basic_profile.user)
            p.autoslug
            p.get_absolute_url()
            p.get_edit_url()
            p.get_admin_url()
        with self.assertNumQueries(1):
            p = self.basic_profile.__class__.get_basic_data(pk=self.basic_profile.pk)
            p.autoslug
            p.get_absolute_url()
            p.get_edit_url()
            p.get_admin_url()
        # Additional database queries are expected when further data of profile is used.
        with self.assertNumQueries(5):
            p = self.basic_profile.__class__.get_basic_data(email=self.basic_profile.email)
            p.age
            p.email_visibility

    def test_absolute_url(self):
        profile = self.basic_profile
        self.assertEqual(
            profile.get_absolute_url(),
            '/profilo/{}/{}/'.format(profile.pk, profile.first_name.lower())
        )

    def test_edit_url(self):
        profile = self.basic_profile
        self.assertEqual(
            profile.get_edit_url(),
            '/profilo/{}/{}/aktualigi/'.format(profile.pk, profile.first_name.lower())
        )

    @override_settings(LANGUAGE_CODE='en')
    def test_admin_url(self):
        profile = self.basic_profile
        self.assertEqual(
            profile.get_admin_url(),
            '/management/hosting/profile/{}/change/'.format(profile.pk)
        )
