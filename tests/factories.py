# https://faker.readthedocs.io/en/latest/providers/faker.providers.person.html
from random import choice

from factory import (
    DjangoModelFactory, Faker, LazyAttribute,
    PostGenerationMethodCall, RelatedFactory, SubFactory,
)

from hosting.models import MR, MRS, PRONOUN_CHOICES

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
