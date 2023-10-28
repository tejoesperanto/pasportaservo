import factory
from factory.django import DjangoModelFactory

from ..models import Product


class ProductReservationFactory(DjangoModelFactory):
    class Meta:
        model = 'shop.Reservation'

    class Params:
        product_code = None

    user = factory.SubFactory('tests.factories.UserFactory', profile=None)
    product = factory.Maybe(
        'product_code',
        yes_declaration=factory.LazyAttribute(
            lambda obj: Product.objects.get(code=obj.product_code)
        ),
        no_declaration=factory.LazyFunction(
            lambda: Product.objects.exclude(code='Donation').order_by('-pk').first()
        ),
    )
    amount = factory.Faker('pyint', min_value=1, max_value=9)

    @factory.lazy_attribute
    def support(self):
        faker = factory.Faker._get_faker()
        faked_support = faker.optional_value(
            'pydecimal', ratio=0.25,
            right_digits=2, min_value=1, max_value=10)
        return faked_support or 0.00
