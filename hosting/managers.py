from django.db import DatabaseError, models
from django.db.models import BooleanField, Case, When
from django.utils import timezone

from core.models import SiteConfiguration


class TrackingManager(models.Manager):
    """
    Adds the following boolean fields from their datetime counterparts:
    'deleted', 'confirmed' and 'checked'
    """

    def get_queryset(self):
        try:
            validity_period = SiteConfiguration.get_solo().confirmation_validity_period
        except DatabaseError:
            from datetime import timedelta
            validity_period = timedelta(weeks=42)
        validity_start = timezone.now() - validity_period
        return super().get_queryset().annotate(
            deleted=Case(
                When(deleted_on__isnull=True, then=False),
                default=True,
                output_field=BooleanField()),
            confirmed=Case(
                When(confirmed_on__isnull=True, then=False),
                When(confirmed_on__lt=validity_start, then=False),
                default=True,
                output_field=BooleanField()),
            checked=Case(
                When(checked_on__isnull=True, then=False),
                # When(checked_on__lt=validity_start, then=False),  # Temporarily disabled.
                default=True,
                output_field=BooleanField()),
        ).select_related()


class NotDeletedManager(TrackingManager):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=True)


class AvailableManager(NotDeletedManager):
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class NotDeletedRawManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_on__isnull=True)


class ActiveStatusManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            is_active=Case(
                When(active_from__gt=timezone.now(), then=False),
                When(active_until__lt=timezone.now(), then=False),
                default=True,
                output_field=BooleanField()),
        )
