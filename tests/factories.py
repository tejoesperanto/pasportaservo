# https://faker.readthedocs.io/en/latest/providers/faker.providers.person.html
from random import choice, randint, random, uniform as uniform_random

from django.contrib.gis.geos import Point

from django_countries.data import COUNTRIES
from django_countries.fields import Country
from factory import (
    DjangoModelFactory, Faker, LazyAttribute, LazyAttributeSequence,
    PostGenerationMethodCall, RelatedFactory, SubFactory, lazy_attribute,
)
from phonenumber_field.phonenumber import PhoneNumber
from slugify import slugify

from hosting.models import MR, MRS, PHONE_TYPE_CHOICES, PRONOUN_CHOICES
from maps import COUNTRIES_WITH_MANDATORY_REGION, SRID
from maps.data import COUNTRIES_GEO

from .constants import PERSON_LOCALES


class LocaleFaker(Faker):
    @classmethod
    def _get_faker(cls, locale=None):
        return super()._get_faker(locale=choice(PERSON_LOCALES))


class AgreementFactory(DjangoModelFactory):
    class Meta:
        model = 'core.Agreement'

    user = SubFactory('tests.factories.UserFactory', agreement=None)
    policy_version = "2018-001"
    withdrawn = None


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'auth.User'

    class Params:
        invalid_email = False

    username = Faker('user_name')
    password = PostGenerationMethodCall('set_password', "adm1n")
    first_name = ""
    last_name = ""
    email = LazyAttribute(
        lambda obj: '{}{}'.format('INVALID_' if obj.invalid_email else '', Faker('email').generate({})))
    is_active = True
    is_staff = False

    profile = RelatedFactory('tests.factories.ProfileFactory', 'user')
    agreement = RelatedFactory(AgreementFactory, 'user')


class StaffUserFactory(UserFactory):
    is_staff = True


class AdminUserFactory(StaffUserFactory):
    is_superuser = True


class ProfileFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Profile'
        django_get_or_create = ('user',)

    user = SubFactory('tests.factories.UserFactory', profile=None)
    title = Faker('random_element', elements=["", MRS, MR])
    first_name = LocaleFaker('first_name')
    last_name = LocaleFaker('last_name')
    names_inversed = False
    pronoun = Faker(
        'random_element', elements=[ch[0] for ch in PRONOUN_CHOICES if ch[0]]
    )
    birth_date = Faker('date_between', start_date='-100y', end_date='-18y')
    description = Faker('paragraph', nb_sentences=4)


class ProfileSansAccountFactory(ProfileFactory):
    class Meta:
        django_get_or_create = None

    user = None


class PlaceFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Place'
        django_get_or_create = ('owner',)

    owner = SubFactory('tests.factories.ProfileFactory')
    country = LazyAttribute(lambda obj: Country(choice(list(COUNTRIES))))
    @lazy_attribute
    def state_province(self):
        if self.country in COUNTRIES_WITH_MANDATORY_REGION or random() > 0.85:
            return Faker('state').generate({})
        else:
            return ""
    city = Faker('city')
    address = Faker('address')
    @lazy_attribute
    def location(self):
        # Cannot use the 'local_latlng' Faker, they don't have all countries in the database!
        return Point(
            [uniform_random(a, b) for a, b in zip(*COUNTRIES_GEO[self.country]['bbox'].values())],
            srid=SRID)
    description = Faker('paragraph', nb_sentences=4)
    short_description = Faker('text', max_nb_chars=140)
    in_book = False


class PhoneFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Phone'
        django_get_or_create = ('profile',)

    profile = SubFactory('tests.factories.ProfileFactory')
    @lazy_attribute
    def number(self):
        # the Faker's phone-number provider is a mess.
        phone = PhoneNumber()
        while not phone.is_valid():
            phone = PhoneNumber(country_code=randint(1, 999), national_number=randint(10000000, 9999999990))
        return phone
    country = LazyAttribute(lambda obj: Country(choice(list(COUNTRIES))))
    comments = Faker('text', max_nb_chars=20)
    type = Faker('random_element', elements=[ch[0] for ch in PHONE_TYPE_CHOICES])


class ConditionFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Condition'
        exclude = ('word',)

    word = Faker('word')
    name = LazyAttribute(lambda obj: '{} {}.'.format(obj.word.title(), obj.word[::-1]))
    abbr = LazyAttributeSequence(lambda obj, n: 'p/{}/{}'.format(obj.word[:6], n))
    slug = LazyAttribute(lambda obj: slugify(obj.abbr, to_lower=True, separator='-'))
