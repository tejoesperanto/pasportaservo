# https://faker.readthedocs.io/en/latest/providers/faker.providers.person.html
from datetime import timedelta
from random import choice, randint, random, uniform as uniform_random

from django.contrib.gis.geos import LineString, Point

import factory
from django_countries.data import COUNTRIES
from django_countries.fields import Country
from factory import DjangoModelFactory, Faker
from phonenumber_field.phonenumber import PhoneNumber
from slugify import slugify

from hosting.models import (
    MR, MRS, PHONE_TYPE_CHOICES, PRONOUN_CHOICES, WHEREABOUTS_TYPE_CHOICES,
)
from maps import COUNTRIES_WITH_MANDATORY_REGION, SRID
from maps.data import COUNTRIES_GEO

from .constants import PERSON_LOCALES


class LocaleFaker(Faker):
    @classmethod
    def _get_faker(cls, locale=None):
        return super()._get_faker(locale=choice(PERSON_LOCALES))


class PolicyFactory(DjangoModelFactory):
    class Meta:
        model = 'core.Policy'

    class Params:
        from_date = None

    url = factory.Sequence(lambda n: "/policy-{:08d}/".format(n))
    title = Faker('sentence')
    content = factory.LazyAttributeSequence(
        lambda obj, n: "{{# {1} #}}<p>Policy {0:03d}</p>\n{2}".format(
            n,
            Faker('date', pattern='%Y-%m-%d').generate({}) if obj.from_date is None else obj.from_date,
            Faker('text').generate({})))


class AgreementFactory(DjangoModelFactory):
    class Meta:
        model = 'core.Agreement'

    user = factory.SubFactory('tests.factories.UserFactory', agreement=None)
    policy_version = "2018-001"
    withdrawn = None


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'auth.User'
        django_get_or_create = ('username',)

    class Params:
        invalid_email = False

    username = Faker('user_name')
    password = factory.PostGenerationMethodCall('set_password', "adm1n")
    first_name = ""
    last_name = ""
    email = factory.LazyAttribute(
        lambda obj: '{}{}'.format('INVALID_' if obj.invalid_email else '', Faker('email').generate({})))
    is_active = True
    is_staff = False

    profile = factory.RelatedFactory('tests.factories.ProfileFactory', 'user')
    agreement = factory.RelatedFactory(AgreementFactory, 'user')


class StaffUserFactory(UserFactory):
    is_staff = True


class AdminUserFactory(StaffUserFactory):
    is_superuser = True


class ProfileFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Profile'
        django_get_or_create = ('user',)

    user = factory.SubFactory('tests.factories.UserFactory', profile=None)
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

    owner = factory.SubFactory('tests.factories.ProfileFactory')
    country = factory.LazyFunction(lambda: Country(choice(list(COUNTRIES))))

    @factory.lazy_attribute
    def state_province(self):
        if self.country in COUNTRIES_WITH_MANDATORY_REGION or random() > 0.85:
            return Faker('state').generate({})
        else:
            return ""

    city = Faker('city')
    address = Faker('address')

    @factory.lazy_attribute
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

    profile = factory.SubFactory('tests.factories.ProfileFactory')

    @factory.lazy_attribute
    def number(self):
        # the Faker's phone-number provider is a mess.
        phone = PhoneNumber()
        while not phone.is_valid():
            phone = PhoneNumber(country_code=randint(1, 999), national_number=randint(10000000, 9999999990))
        return phone

    country = factory.LazyFunction(lambda: Country(choice(list(COUNTRIES))))
    comments = Faker('text', max_nb_chars=20)
    type = Faker('random_element', elements=[ch[0] for ch in PHONE_TYPE_CHOICES])


class ConditionFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Condition'
        exclude = ('word',)

    word = Faker('word')
    name = factory.LazyAttribute(lambda obj: '{} {}.'.format(obj.word.title(), obj.word[::-1]))
    abbr = factory.LazyAttributeSequence(lambda obj, n: 'p/{}/{}'.format(obj.word[:6], n))
    slug = factory.LazyAttribute(lambda obj: slugify(obj.abbr, to_lower=True, separator='-'))


class GenderFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Gender'
        django_get_or_create = ('name_en', 'name')
        strategy = factory.BUILD_STRATEGY

    id = factory.Sequence(
        lambda n: GenderFactory._meta.get_model_class().objects.values('id').last()['id'] + n + 1)
    name_en = Faker('word')
    name = factory.LazyFunction(
        lambda: ' '.join(Faker('words', locale='la', nb=2).generate({})))


class WhereaboutsFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.Whereabouts'

    type = Faker('random_element', elements=[ch[0] for ch in WHEREABOUTS_TYPE_CHOICES])
    name = Faker('city')

    @factory.lazy_attribute
    def state(self):
        if self.country in COUNTRIES_WITH_MANDATORY_REGION or random() > 0.85:
            return Faker('state').generate({})
        else:
            return ""

    country = factory.LazyFunction(lambda: Country(choice(list(COUNTRIES))))

    @factory.lazy_attribute
    def bbox(self):
        minx, miny, maxx, maxy = self.center.buffer(width=uniform_random(0.05, 0.45), quadsegs=2).extent
        return LineString((minx, miny), (maxx, maxy), srid=SRID)

    @factory.lazy_attribute
    def center(self):
        # Cannot use the 'local_latlng' Faker, they don't have all countries in the database!
        return Point(
            [uniform_random(a, b) for a, b in zip(*COUNTRIES_GEO[self.country]['bbox'].values())],
            srid=SRID)


class TravelAdviceFactory(DjangoModelFactory):
    class Meta:
        model = 'hosting.TravelAdvice'

    class Params:
        in_past, in_present, in_future = None, None, None

    content = Faker('paragraph')
    description = factory.LazyAttribute(lambda obj: '<p>{}</p>'.format(obj.content))

    @factory.lazy_attribute
    def countries(self):
        return Faker('random_elements', elements=COUNTRIES.keys(), unique=True, length=randint(1, 4)).generate({})

    @factory.lazy_attribute
    def active_from(self):
        if self.in_past:
            faked_date = Faker('date_between', start_date='-365d', end_date='-200d') if random() < 0.85 else None
        elif self.in_future:
            faked_date = Faker('date_between', start_date='+2d', end_date='+199d')
        elif self.in_present:
            faked_date = Faker('date_between', start_date='-200d', end_date='-2d') if random() < 0.85 else None
        else:
            faked_date = Faker('date_object', end_datetime='+5y') if random() < 0.85 else None
        return faked_date.generate({}) if faked_date else None

    @factory.lazy_attribute
    def active_until(self):
        if self.in_past:
            faked_date = Faker('date_between', start_date='-199d', end_date='-2d')
        elif self.in_future:
            faked_date = Faker('date_between', start_date='+200d', end_date='+365d') if random() < 0.85 else None
        elif self.in_present:
            faked_date = Faker('date_between', start_date='+2d', end_date='+200d') if random() < 0.85 else None
        else:
            if self.active_from:
                start, end = self.active_from, self.active_from + timedelta(days=365)
                faked_date = Faker('date_between_dates', date_start=start, date_end=end) if random() < 0.85 else None
            else:
                faked_date = Faker('date_object', end_datetime='+5y') if random() < 0.85 else None
        return faked_date.generate({}) if faked_date else None
