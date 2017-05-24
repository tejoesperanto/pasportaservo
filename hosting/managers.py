from django.db import models
from django.db.models import BooleanField, Case, When
from django.utils import timezone

from core.models import SiteConfiguration

config = SiteConfiguration.objects.get()


class TrackingManager(models.Manager):
    """ Adds the following boolean fields from their datetime counterpart:
        'deleted', 'confirmed' and 'checked'
    """

    def get_queryset(self):
        validity_start = timezone.now() - config.confirmation_validity_period
        return super().get_queryset().annotate(deleted=Case(
            When(deleted_on__isnull=True, then=False),
            default=True,
            output_field=BooleanField()
        )).annotate(confirmed=Case(
            When(confirmed_on__isnull=True, then=False),
            When(confirmed_on__lt=validity_start, then=False),
            default=True,
            output_field=BooleanField()
        )).annotate(checked=Case(
            When(checked_on__isnull=True, then=False),
            When(checked_on__lt=validity_start, then=False),
            default=True,
            output_field=BooleanField()
        ))


class NotDeletedManager(TrackingManager):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=True)


class AvailableManager(NotDeletedManager):
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class AvailableWithCoordManager(AvailableManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
