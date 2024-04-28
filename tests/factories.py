# https://faker.readthedocs.io/en/latest/providers/faker.providers.person.html
import re
from datetime import timedelta
from hashlib import md5
from random import choice, randint, random, uniform as uniform_random
from typing import Generic, TypeVar

from django.contrib.gis.geos import LineString, Point
from django.db.models import Model
from django.utils import timezone

import factory
import faker
import rstr
from django_countries.data import COUNTRIES
from factory import Faker
from factory.django import DjangoModelFactory
from phonenumber_field.phonenumber import PhoneNumber

from core.models import Agreement, Policy, UserBrowser
from hosting.countries import COUNTRIES_DATA, countries_with_mandatory_region
from hosting.models import (
    Condition, CountryRegion, Gender, LocationType, PasportaServoUser,
    Phone, Place, Profile, TravelAdvice, Whereabouts,
)
from maps import SRID
from maps.data import COUNTRIES_GEO

from .constants import PERSON_LOCALES


class LocaleFaker(Faker):
    _FAKER_REGISTRY = {}

    @classmethod
    def _get_faker(cls, locale=None):
        if locale is None:
            locale = choice(PERSON_LOCALES)
        if locale not in cls._FAKER_REGISTRY:
            cls._FAKER_REGISTRY[locale] = faker.Faker(
                locale=locale, **fake_providers('person', 'python', 'lorem')
            )
        return cls._FAKER_REGISTRY[locale]


class OptionalProvider(faker.providers.BaseProvider):
    """
    Faker provider that generates optional data (a value or a None).
    Inspired by OptionalProvider by lyz-code, licensed under GPLv3:
    https://github.com/lyz-code/faker-optional
    """
    def optional_value(self, fake, ratio=0.85, **kwargs):
        if random() > ratio:
            return None
        else:
            return self.generator.format(fake, **kwargs)


def fake_providers(*providers):
    return {
        'providers': [f'faker.providers.{p}' for p in providers]
    }


Faker.add_provider(OptionalProvider)


ModelType = TypeVar('ModelType', bound=Model)


class TypedDjangoModelFactory(DjangoModelFactory, Generic[ModelType]):
    @classmethod
    def build(cls, **kwargs) -> ModelType:
        return super().build(**kwargs)

    @classmethod
    def build_batch(cls, size: int, **kwargs) -> list[ModelType]:
        return super().build_batch(size, **kwargs)

    @classmethod
    def create(cls, **kwargs) -> ModelType:
        return super().create(**kwargs)

    @classmethod
    def create_batch(cls, size: int, **kwargs) -> list[ModelType]:
        return super().create_batch(size, **kwargs)


class PolicyFactory(TypedDjangoModelFactory[Policy]):
    class Meta:
        model = 'core.Policy'

    class Params:
        from_past_date, from_future_date = None, None
        with_summary = True

    @classmethod
    def _setup_next_sequence(cls):
        return 1

    version = factory.Sequence(lambda n: f"{n:08d}")

    @factory.lazy_attribute
    def effective_date(self):
        faker = Faker._get_faker()
        if self.from_past_date:
            faked_date = faker.date_between(start_date='-10y', end_date='-1y')
        elif self.from_future_date:
            faked_date = faker.date_between(start_date='+1y', end_date='+10y')
        else:
            faked_date = faker.date_this_decade(before_today=True, after_today=True)
        return faked_date

    @factory.lazy_attribute
    def content(self):
        faker = Faker._get_faker(locale='la')
        policy_text = faker.text()
        return f"<p>Policy {self.version}</p>\n{policy_text}"

    @factory.lazy_attribute
    def changes_summary(self):
        faker = Faker._get_faker(locale='la')
        if self.with_summary is None:
            return faker.optional_value('paragraph')
        elif self.with_summary:
            return faker.paragraph()
        else:
            return ""


class AgreementFactory(TypedDjangoModelFactory[Agreement]):
    class Meta:
        model = 'core.Agreement'

    user = factory.SubFactory('tests.factories.UserFactory', agreement=None, profile=None)

    @factory.lazy_attribute
    def policy_version(self):
        # By default, set the latest effective policy's version
        # (future policies are not yet effective).
        return (
            PolicyFactory._meta.get_model_class().objects
            .filter(effective_date__lte=timezone.now())
            .order_by('-effective_date')
            .values_list('version', flat=True)
            .first()
            or "UNKNOWN"
        )

    withdrawn = None


class UserFactory(TypedDjangoModelFactory[PasportaServoUser]):
    class Meta:
        model = 'auth.User'
        django_get_or_create = ('username',)

    class Params:
        deceased_user = False
        deleted_profile = False

    username = Faker('user_name')
    password = factory.PostGenerationMethodCall('set_password', "adm1n")
    first_name = ""
    last_name = ""
    email = Faker('email', safe=False)
    is_active = True
    is_staff = False
    is_superuser = False

    profile = factory.RelatedFactory(
        'tests.factories.ProfileFactory', 'user',
        deceased=factory.SelfAttribute('..deceased_user'),
        deleted=factory.SelfAttribute('..deleted_profile'))
    agreement = factory.RelatedFactory('tests.factories.AgreementFactory', 'user')

    @factory.post_generation
    def invalid_email(instance, create, value, **kwargs):
        instance._clean_email = instance.email
        if value:
            instance.email = f'INVALID_{instance.email}'

    @factory.post_generation
    def places(instance, create, value, **kwargs):
        if not create or not value or not hasattr(instance, 'profile'):
            return
        ProfileFactory.generate_places(instance.profile, value, **kwargs)


class StaffUserFactory(UserFactory):
    is_staff = True


class AdminUserFactory(StaffUserFactory):
    is_superuser = True


class UserBrowserFactory(TypedDjangoModelFactory[UserBrowser]):
    class Meta:
        model = 'core.UserBrowser'
        exclude = ('BROWSERS', 'browser', 'PLATFORMS', 'platform', 'platform_token')

    BROWSERS = {
        'chrome': ("Google Chrome", r'Chrome/([0-9.]+)'),
        'firefox': ("Mozilla Firefox", r'Firefox/([0-9.]+)'),
        'internet_explorer': ("MSIE", r'MSIE ([0-9.]+)'),
        'opera': ("Opera", r'Version/([0-9.]+)'),
        'safari': ("Apple Safari", r'Version/([0-9.]+)'),
    }
    PLATFORMS = {
        'android': r'(Android) ([0-9.]+)',
        'ios': r'(i[a-zA-Z]+ OS) ([0-9_]+)',
        'linux': r'(Linux) ()',
        'mac': r'(Mac OS X) ([0-9_]+)',
        'windows': r'(Windows) (.+)',
    }

    user = factory.SubFactory('tests.factories.UserFactory', profile=None)
    browser = Faker('random_element', elements=BROWSERS.keys())
    user_agent_string = factory.LazyAttribute(lambda obj: getattr(Faker._get_faker(), obj.browser)())
    user_agent_hash = factory.LazyAttribute(lambda obj: md5(obj.user_agent_string.encode('utf-8')).hexdigest())
    browser_name = factory.LazyAttribute(lambda obj: obj.BROWSERS[obj.browser][0])

    @factory.lazy_attribute
    def browser_version(self):
        m = re.search(self.BROWSERS[self.browser][1], self.user_agent_string)
        return m.group(1) if m else ''

    platform = Faker('random_element', elements=PLATFORMS.keys())

    @factory.lazy_attribute
    def platform_token(self):
        return re.search(
            self.PLATFORMS[self.platform],
            getattr(Faker._get_faker(), f'{self.platform}_platform_token')()
        )

    os_name = factory.LazyAttribute(lambda obj: obj.platform_token.group(1) if obj.platform_token else '')
    os_version = factory.LazyAttribute(lambda obj: obj.platform_token.group(2) if obj.platform_token else '')

    @factory.lazy_attribute
    def device_type(self):
        if not self.platform_token:
            return ''
        platform = self.platform_token.group(1)
        return (
            "Smartphone" if platform.startswith('iPhone') or platform == 'Android'
            else "Tablet" if platform.startswith('iPad')
            else "PC"
        )


class ProfileFactory(TypedDjangoModelFactory[Profile]):
    class Meta:
        model = 'hosting.Profile'
        django_get_or_create = ('user',)
        exclude = ('generated_name',)

    class Params:
        deleted = False
        deceased = False
        with_email = False
        locale = None

    user = factory.SubFactory('tests.factories.UserFactory', profile=None)
    title = Faker('random_element', elements=[title or "" for title in Profile.Titles.values])
    generated_name = factory.LazyAttribute(
        lambda obj:
            LocaleFaker._get_faker(obj.locale).pystr_format(string_format='{{first_name}}//{{last_name}}')
    )
    first_name = factory.LazyAttribute(lambda obj: obj.generated_name.split('//')[0])
    last_name = factory.LazyAttribute(lambda obj: obj.generated_name.split('//')[1])
    names_inversed = False
    pronoun = Faker(
        'random_element', elements=list(filter(None, Profile.Pronouns.values))
    )
    birth_date = Faker('date_between', start_date='-100y', end_date='-18y')
    death_date = factory.Maybe(
        'deceased',
        yes_declaration=Faker('date_this_decade'),
        no_declaration=None)
    description = Faker('paragraph', nb_sentences=4)
    email = factory.Maybe(
        'with_email',
        yes_declaration=Faker('email', safe=False),
        no_declaration="")
    deleted_on = factory.Maybe(
        'deleted',
        yes_declaration=timezone.now(),
        no_declaration=None)

    @factory.post_generation
    def invalid_email(instance, create, value, **kwargs):
        instance._clean_email = instance.email
        if value and instance.email:
            instance.email = f'INVALID_{instance.email}'

    @staticmethod
    def generate_places(instance, value, **kwargs):
        try:
            values_iterator = iter(value)
        except TypeError:
            if isinstance(value, int):
                values_iterator = PlaceFactory.build_batch(value, owner=None, **kwargs)
            else:
                values_iterator = []
        for place in values_iterator:
            if isinstance(place, dict):
                place = PlaceFactory.build(owner=None, **(kwargs | place))
            place.owner = instance
            place.save()

    @factory.post_generation
    def places(instance, create, value, **kwargs):
        if not create or not value or instance.user is None:
            return
        ProfileFactory.generate_places(instance, value, **kwargs)


class ProfileSansAccountFactory(ProfileFactory):
    class Meta:
        django_get_or_create = None

    user = None


class PlaceFactory(TypedDjangoModelFactory[Place]):
    class Meta:
        model = 'hosting.Place'

    class Params:
        deleted = False
        deleted_profile = False

    owner = factory.SubFactory(
        'tests.factories.ProfileFactory',
        deleted=factory.SelfAttribute('..deleted_profile'))
    country = Faker('random_element', elements=COUNTRIES.keys())
    city = Faker('city')
    address = Faker('address')

    @factory.lazy_attribute
    def state_province(self):
        if self.country in countries_with_mandatory_region():
            region = CountryRegionFactory(country=self.country)
            return region.iso_code
        else:
            return ""

    @factory.lazy_attribute
    def location(self):
        # Cannot use the 'local_latlng' Faker, they don't have all countries in the database!
        return Point(
            [uniform_random(a, b) for a, b in zip(*COUNTRIES_GEO[self.country]['bbox'].values())],
            srid=SRID)

    description = Faker('paragraph', nb_sentences=4)
    short_description = Faker('text', max_nb_chars=140)
    in_book = False
    deleted_on = factory.Maybe(
        'deleted',
        yes_declaration=timezone.now(),
        no_declaration=None)

    @staticmethod
    def generate_postcode(country):
        regex = COUNTRIES_DATA[country]['postcode_regex'] or r'\d{5}'
        # The * repetition qualifier makes the generator go wild, strictly limit to 1 copy.
        regex = regex.replace('*', '{1}')
        # Articially limit the length of overly permissive chunks.
        regex = re.sub(r'{0,\d\d}', '{0,2}', regex)
        # Generate a random value according to the constrained regular expression.
        # All whitespaces are condensed to single space and the value is uppercased.
        value = ""
        while value in ("", "GIR0AA", "GIR 0AA"):
            # The generator has a strong preference to this UK postal code...
            value = ' '.join(rstr.xeger(regex).upper().strip().split())
        return value

    @factory.post_generation
    def postcode(instance, create, value, **kwargs):
        if not value:
            return
        if value is True:
            instance.postcode = PlaceFactory.generate_postcode(instance.country)
        else:
            instance.postcode = value


class PhoneFactory(TypedDjangoModelFactory[Phone]):
    class Meta:
        model = 'hosting.Phone'

    profile = factory.SubFactory('tests.factories.ProfileFactory')

    @factory.lazy_attribute
    def number(self):
        # the Faker's phone-number provider is a mess.
        phone = PhoneNumber()
        while not phone.is_valid():
            phone = PhoneNumber(country_code=randint(1, 999), national_number=randint(10000, 99999999990))
        return phone

    country = Faker('random_element', elements=COUNTRIES.keys())
    comments = Faker('text', max_nb_chars=20)
    type = Faker('random_element', elements=Phone.PhoneType.values)


class ConditionFactory(TypedDjangoModelFactory['Condition']):
    class Meta:
        model = 'hosting.Condition'
        exclude = ('word',)

    word = Faker('word')
    name_en = factory.LazyAttribute(
        lambda obj:
            '{} {} {}.'.format(obj.word.title(), obj.word[::-1], obj.word)
    )
    name = factory.LazyAttribute(
        lambda obj:
            LocaleFaker._get_faker('la')
            .pystr_format(string_format='{{word}} {{word}}.')
            .title()
    )
    abbr = factory.LazyAttributeSequence(lambda obj, n: 'p/{}/{}'.format(obj.word[:6], n))
    category = Faker('random_element', elements=Condition.Categories.values)
    restriction = Faker('boolean', chance_of_getting_true=75)


class GenderFactory(TypedDjangoModelFactory[Gender]):
    class Meta:
        model = 'hosting.Gender'
        django_get_or_create = ('name_en', 'name')
        strategy = factory.BUILD_STRATEGY

    @classmethod
    def _setup_next_sequence(cls):
        last_existing_id = (
            GenderFactory._meta.get_model_class().objects
            .order_by('id').values('id').last()
        )
        return last_existing_id['id'] + 2 if last_existing_id is not None else 1

    # When a custom gender (not present in DB) is provided by the user, a fake
    # `Gender` object is created but not saved to the database. Its ID must be
    # explicitely set to avoid the "save() prohibited, unsaved related object"
    # errors for other models.
    id = factory.Sequence(lambda n: n)
    name_en = Faker('word')
    name = Faker('pystr_format', string_format='{{word}} {{word}}', locale='la')


class CountryRegionFactory(TypedDjangoModelFactory[CountryRegion]):
    class Meta:
        model = 'hosting.CountryRegion'

    class Params:
        short_code = factory.LazyFunction(lambda: random() < 0.20)

    country = Faker('random_element', elements=COUNTRIES.keys())
    iso_code = Faker('pystr_format', string_format='???#', letters='ABCDEFGHJKLMNPQRSTUVWXYZ')
    latin_code = factory.Maybe(
        'short_code',
        yes_declaration=Faker('pystr_format', string_format='??', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        no_declaration=Faker('sentence', nb_words=3))
    latin_name = factory.Maybe(
        'short_code',
        yes_declaration=Faker('sentence', nb_words=3),
        no_declaration="")

    @factory.lazy_attribute
    def esperanto_name(self):
        latin_region = self.latin_name or self.latin_code
        replacements = [
            ('Q', 'Kv'), ('q', 'kv'),
            ('W', 'V'), ('w', 'v'),
            ('X', 'Ks'), ('x', 'ks'),
            ('Y', 'J'), ('y ', 'i '), ('y.', 'i.'), ('y', 'j'),
            ('Ph', 'F'), ('ph', 'f'),
            ('Th', 'Z'), ('th', 'z'),
            ('cc', 'k'), ('ee', 'i'), ('ll', 'l'), ('tt', 't'),
            (' ', '-'), ('.', 'o'),
        ]
        for lat_letter, esp_letter in replacements:
            latin_region = latin_region.replace(lat_letter, esp_letter)
        return latin_region


class WhereaboutsFactory(TypedDjangoModelFactory[Whereabouts]):
    class Meta:
        model = 'hosting.Whereabouts'

    type = Faker('random_element', elements=[ch.value for ch in LocationType])

    @factory.lazy_attribute
    def name(self):
        return Faker._get_faker().city().upper()

    @factory.lazy_attribute
    def state(self):
        if self.country in countries_with_mandatory_region():
            return CountryRegionFactory(country=self.country).iso_code
        else:
            return ""

    country = Faker('random_element', elements=COUNTRIES.keys())

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


class TravelAdviceFactory(TypedDjangoModelFactory[TravelAdvice]):
    class Meta:
        model = 'hosting.TravelAdvice'

    class Params:
        in_past, in_present, in_future = None, None, None

    content = Faker('paragraph')
    description = factory.LazyAttribute(lambda obj: '<p>{}</p>'.format(obj.content))
    countries = Faker(
        'random_elements',
        elements=COUNTRIES.keys(),
        unique=True, length=factory.LazyFunction(lambda: randint(1, 4)))

    @factory.lazy_attribute
    def active_from(self):
        faker = Faker._get_faker()
        if self.in_past:
            faked_date = faker.optional_value('date_between', start_date='-365d', end_date='-200d')
        elif self.in_future:
            faked_date = faker.date_between(start_date='+2d', end_date='+199d')
        elif self.in_present:
            faked_date = faker.optional_value('date_between', start_date='-200d', end_date='-2d')
        else:
            faked_date = faker.optional_value('date_object', end_datetime='+5y')
        return faked_date

    @factory.lazy_attribute
    def active_until(self):
        faker = Faker._get_faker()
        if self.in_past:
            faked_date = faker.date_between(start_date='-199d', end_date='-2d')
        elif self.in_future:
            faked_date = faker.optional_value('date_between', start_date='+200d', end_date='+365d')
        elif self.in_present:
            faked_date = faker.optional_value('date_between', start_date='+2d', end_date='+200d')
        else:
            if self.active_from:
                start, end = self.active_from, self.active_from + timedelta(days=365)
                faked_date = faker.optional_value('date_between_dates', date_start=start, date_end=end)
            else:
                faked_date = faker.optional_value('date_object', end_datetime='+5y')
        return faked_date
