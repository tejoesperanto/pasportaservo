from random import sample

from django.contrib.auth.models import Group
from django.template import Context, Template
from django.test import TestCase, tag

from django_countries.data import COUNTRIES

from tests import UserTag
from tests.factories import (
    AdminUserFactory, PhoneFactory, ProfileFactory, UserFactory,
)


@tag('templatetags')
class SupervisorsFilterTests(TestCase):
    template = Template(
        "{% load supervisors from book %}"
        "{{ country|supervisors|safe }}"
    )

    def test_country_code_empty(self):
        with self.assertRaises(Group.DoesNotExist):
            self.template.render(Context())
        with self.assertRaises(Group.DoesNotExist):
            self.template.render(Context({'country': ""}))

    def test_country_code_no_supervisors(self):
        Group.objects.get_or_create(name='AQ')
        page = self.template.render(Context({'country': "AQ"}))
        self.assertEqual(page, str([]))

    def test_country_code_with_supervisors(self):
        supervised_countries = sample(list(COUNTRIES), 2)
        country_code = supervised_countries[0]
        all_users = {
            UserTag(f'country:{supervised_countries[0]}', 'profile:true'):
                UserFactory.create(locale='sv'),
            UserTag(f'country:{supervised_countries[0]}', 'profile:true', 'inactive'):
                UserFactory.create(is_active=False),
            UserTag(f'country:{supervised_countries[0]}', 'profile:true', 'deceased'):
                UserFactory.create(deceased_user=True),
            UserTag(f'country:{supervised_countries[0]}', 'profile:deleted'):
                UserFactory.create(deleted_profile=True),
            UserTag(f'country:{supervised_countries[0]}', 'profile:deleted', 'deceased'):
                UserFactory.create(deleted_profile=True, deceased_user=True),
            UserTag(f'country:{supervised_countries[0]}', 'profile:false'):
                UserFactory.create(profile=None),
            UserTag(f'country:{supervised_countries[0]}', 'profile:false', 'inactive'):
                UserFactory.create(profile=None, is_active=False),
            UserTag(f'country:{supervised_countries[0]}', 'profile:false', 'deceased'):
                UserFactory.create(profile=None, deceased_user=True),
            UserTag('superuser'):
                AdminUserFactory.create(),
            UserTag(f'country:{supervised_countries[1]}', 'profile:true'):
                UserFactory.create(locale='sv'),
            UserTag('country:both', 'profile:true'):
                UserFactory.create(locale='sv'),
            UserTag('country:both', 'profile:false'):
                UserFactory.create(locale='sv', profile=None),
        }

        for c in supervised_countries:
            Group.objects.get_or_create(name=c)[0].user_set.add(*(
                user for user_tag, user in all_users.items()
                if user_tag.matches_any(f'country:{c}', 'country:both')
            ))

        page = self.template.render(Context({'country': country_code}))
        expected_users = sorted(
            user.profile for user_tag, user in all_users.items()
            if user_tag.matches_any(f'country:{country_code}', 'country:both')
            and 'profile:true' in user_tag
            and user_tag.matches_none('inactive', 'deceased')
        )
        self.assertEqual(page, str(expected_users), msg=(
            f"Expected {len(expected_users)} supervisors but seen {page.count('#')}."
            if len(expected_users) != page.count('#') else "Expected other supervisors."
        ))


@tag('templatetags')
class LatexIconFilterTests(TestCase):
    template = Template(
        "{% load latex_icon from book %}"
        "{{ object|latex_icon }}"
    )

    def test_unexpected_object(self):
        page = self.template.render(Context({'object': ProfileFactory.create()}))
        self.assertEqual(page, "")

    def test_phone_object(self):
        test_data = {
            PhoneFactory._meta.model.PhoneType.MOBILE: r"{\faMobile*}",
            PhoneFactory._meta.model.PhoneType.HOME: r"{\faPhone*}",
            PhoneFactory._meta.model.PhoneType.WORK: r"{\faPhone*}",
            PhoneFactory._meta.model.PhoneType.FAX: r"{\faFax}",
            'xyz': r"{\faPhone*}",
        }
        phone = PhoneFactory.create()
        for phone_type, expected_icon in test_data.items():
            with self.subTest(type=phone_type):
                phone.type = phone_type
                page = self.template.render(Context({'object': phone}))
                self.assertIn(expected_icon, page)


@tag('templatetags')
class PublicPhoneNumbersTagTests(TestCase):
    template = Template(
        "{% load get_public_phone_numbers from book %}"
        "{% get_public_phone_numbers profile as phones %}"
        "count={{ phones|length }}; "
        "{% for phone in phones %}{{ phone }}; {% endfor %}"
    )

    @classmethod
    def setUpTestData(cls):
        cls.profile = ProfileFactory.create()

    def test_missing_profile(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context())
        with self.assertRaises(AttributeError):
            self.template.render(Context({'profile': None}))

    def test_no_phones(self):
        self.assertEqual(self.profile.phones.count(), 0)
        page = self.template.render(Context({'profile': self.profile}))
        self.assertEqual(page, "count=0; ")

    def test_hidden_phones(self):
        phones = [
            PhoneFactory.create(
                visibility_value__in_book=False, profile=self.profile),
            PhoneFactory.create(
                visibility_value__in_book=False, profile=self.profile, deleted=True),
            PhoneFactory.create(
                visibility_value__in_book=False),  # Different owner.
        ]
        self.profile.set_phone_order([phones[1].pk, phones[0].pk])
        self.assertEqual(self.profile.phones.count(), 2)

        page = self.template.render(Context({'profile': self.profile}))
        self.assertEqual(page, "count=0; ")

    def test_visible_phones(self):
        phones = [
            PhoneFactory.create(
                visibility_value__in_book=True, profile=self.profile),
            PhoneFactory.create(
                visibility_value__in_book=True, profile=self.profile),
            PhoneFactory.create(
                visibility_value__in_book=True, profile=self.profile, deleted=True),
            PhoneFactory.create(
                visibility_value__in_book=True),  # Different owner.
        ]
        self.profile.set_phone_order([phones[1].pk, phones[2].pk, phones[0].pk])
        self.assertEqual(self.profile.phones.count(), 3)

        page = self.template.render(Context({'profile': self.profile}))
        self.assertEqual(
            page,
            "count=2; "
            f"{phones[1].number.as_international}; {phones[0].number.as_international}; "
        )
