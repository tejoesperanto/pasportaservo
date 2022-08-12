from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_extensions.db.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField(
        _("name"), max_length=50)
    code = models.CharField(
        _("code"), max_length=20, unique=True)
    price = models.DecimalField(
        _("price"),
        default=Decimal('8.99'),
        max_digits=4, decimal_places=2)
    low_price = models.DecimalField(
        _("low price"),
        default=Decimal('2.99'),
        max_digits=4, decimal_places=2)

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{} {}: {}>".format(self.__class__.__name__, self.id, self.code)


class Reservation(TimeStampedModel):
    product = models.ForeignKey(
        'shop.Product', verbose_name=_("product"),
        on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"),
        on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(
        _("amount"),
        default=1)
    discount = models.BooleanField(
        _("TEJO discount"),
        default=False,
        # Translator: xgettext:no-python-format
        help_text=_("If you are member of TEJO or UEA "
                    "and the 10% discount applies (twice a year)."))
    support = models.DecimalField(
        _("support"),
        default=Decimal('0.00'),
        max_digits=6, decimal_places=2)

    class Meta:
        verbose_name = _("reservation")
        verbose_name_plural = _("reservations")
        unique_together = (('product', 'user'))

    def __str__(self):
        return " - ".join((self.product.code, str(self.user)))

    def __repr__(self):
        st = "{} + support: {}" if self.support else "{}"
        return st.format(self.amount, self.support)

    def get_absolute_url(self):
        return reverse('reservation', kwargs={'product_code': self.product.code})

    def get_edit_url(self):
        return reverse('reserve', kwargs={'product_code': self.product.code})
