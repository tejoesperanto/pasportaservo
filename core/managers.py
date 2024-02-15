from typing import TYPE_CHECKING, Any

from django.core.cache import cache
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from .models import Policy


class PoliciesManager(models.Manager):
    use_in_migrations = True

    def latest_efective(self, requiring_consent: bool = False) -> 'Policy':
        policy_filter: dict[str, Any] = {
            'effective_date__lte': timezone.now(),
        }
        if requiring_consent:
            policy_filter['requires_consent'] = True
        return self.filter(**policy_filter).latest()

    def all_effective(self) -> tuple[list[str], 'PoliciesManager']:
        today = timezone.now()
        cache_key = f'all-effective-policies_{today:%Y-%m-%d}'
        cached_policy_ids = cache.get(cache_key)
        if cached_policy_ids is not None:
            policies = self.filter(version__in=cached_policy_ids)
        else:
            latest_policy_requiring_consent = (
                self
                .filter(effective_date__lte=today, requires_consent=True)
                .order_by('-effective_date')
            )[0:1]
            policies = self.filter(
                effective_date__lte=today,
                effective_date__gte=latest_policy_requiring_consent.values('effective_date'),
            )
            # Store the effective policies in the cache for one day.
            # If a version identifier of a policy is changed during that day, users
            # might see an incorrect policy – but that shouldn't happen in practice.
            cached_policy_ids = list(policies.values_list('version', flat=True))
            cache.set(cache_key, cached_policy_ids, int(24.5 * 60 * 60))
        return (cached_policy_ids, policies.order_by('-effective_date'))
