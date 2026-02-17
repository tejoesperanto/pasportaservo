import factory
from postman.models import Message

from tests.factories import TypedDjangoModelFactory, UserFactory

__all__ = [
    'ChatMessageFactory',
    'UserFactory',
]


class ChatMessageFactory(TypedDjangoModelFactory[Message]):
    class Meta:
        model = Message

    sender = factory.SubFactory('tests.factories.UserFactory')
    recipient = factory.SubFactory('tests.factories.UserFactory')
    subject = factory.Faker('sentence')
    body = factory.Faker('paragraph')
