from datetime import timedelta, timezone

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from slugify import slugify


class PostFactory(DjangoModelFactory):
    class Meta:
        model = 'blog.Post'
        exclude = ('first_para', 'rest_of_text',)

    class Params:
        is_published = True
        will_be_published = False

    title = factory.Faker('sentence', nb_words=7)
    slug = factory.LazyAttribute(lambda obj: slugify(obj.title, separator='-')[:50])
    first_para = factory.Faker('text', max_nb_chars=150)
    rest_of_text = factory.Faker('text', max_nb_chars=250)
    description = factory.LazyAttribute(
        lambda obj: obj.first_para)
    body = factory.LazyAttribute(
        lambda obj: "{} {}".format(obj.first_para, obj.rest_of_text))
    content = factory.LazyAttribute(
        lambda obj: "{}---- {}".format(obj.first_para, obj.rest_of_text))
    pub_date = factory.LazyAttribute(
        lambda obj: (
            getattr(Faker(), 'date_time_this_decade' if not obj.will_be_published else 'future_datetime')(
                tzinfo=timezone(timedelta(hours=1))
            )
            if obj.is_published else None
        ))
    author = factory.SubFactory('tests.factories.UserFactory', profile=None)
