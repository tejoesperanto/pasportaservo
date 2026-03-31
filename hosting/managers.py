from typing import TYPE_CHECKING, TypeVar

from django.db import DatabaseError, models
from django.db.models import BooleanField, Case, Q, When
from django.utils import timezone

from waffle import get_waffle_switch_model

from core.models import SiteConfiguration

if TYPE_CHECKING:
    from hosting.models import TrackingModel
    TrackingModelT = TypeVar('TrackingModelT', bound=TrackingModel)


class TrackingManager(models.Manager['TrackingModelT']):
    """
    Adds the following boolean fields from their datetime counterparts:
    'deleted', 'confirmed' and 'checked'
    """

    def get_queryset(self):
        try:
            validity_period = SiteConfiguration.get_solo().confirmation_validity_period
        except DatabaseError:
            validity_period = timezone.timedelta(weeks=42)
        validity_start = timezone.now() - validity_period

        SiteSwitch = get_waffle_switch_model()
        try:
            confirmation_expiration = (
                SiteSwitch.get('HOSTING_DATA_CONFIRMATION_EXPIRY').is_active()
            )
        except DatabaseError:
            confirmation_expiration = True
        try:
            verification_expiration = (
                SiteSwitch.get('HOSTING_DATA_VERIFICATION_EXPIRY').is_active()
            )
        except DatabaseError:
            verification_expiration = False
        confirmation_validity_condition = (
            Q(confirmed_on__lt=validity_start) if confirmation_expiration
            else Q(confirmed_on__in=[])  # Always-false condition.
        )
        verification_validity_condition = (
            Q(checked_on__lt=validity_start) if verification_expiration
            else Q(checked_on__in=[])  # Always-false condition.
        )

        return super().get_queryset().annotate(
            deleted=Case(
                When(deleted_on__isnull=True, then=False),
                default=True,
                output_field=BooleanField()),
            confirmed=Case(
                When(confirmed_on__isnull=True, then=False),
                When(confirmation_validity_condition, then=False),
                default=True,
                output_field=BooleanField()),
            checked=Case(
                When(checked_on__isnull=True, then=False),
                When(verification_validity_condition, then=False),
                default=True,
                output_field=BooleanField()),
        ).select_related()


class NotDeletedManager(TrackingManager['TrackingModelT']):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=True)


class AvailableManager(NotDeletedManager['TrackingModelT']):
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class NotDeletedRawManager(models.Manager['TrackingModelT']):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_on__isnull=True)


class ActiveStatusManager[ActiveModelT: models.Model](models.Manager[ActiveModelT]):
    def get_queryset(self):
        return super().get_queryset().annotate(
            is_active=Case(
                When(active_from__gt=timezone.now(), then=False),
                When(active_until__lt=timezone.now(), then=False),
                default=True,
                output_field=BooleanField()),
        )
