from django.db import ProgrammingError, models
from django.db.models import BooleanField, Case, When
from django.utils import timezone

from core.models import SiteConfiguration


class TrackingManager(models.Manager):
    """ Adds the following boolean fields from their datetime counterpart:
        'deleted', 'confirmed' and 'checked'
    """

    def get_queryset(self):
        try:
            validity_period = SiteConfiguration.get_solo().confirmation_validity_period
        except ProgrammingError:
            from datetime import timedelta
            validity_period = timedelta(weeks=42)
        validity_start = timezone.now() - validity_period
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
        )).select_related()


class NotDeletedManager(TrackingManager):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=True)


class AvailableManager(NotDeletedManager):
    def get_queryset(self):
        return super().get_queryset().filter(available=True)
