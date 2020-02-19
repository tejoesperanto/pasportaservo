import re
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from solo.models import SingletonModel

from .managers import PoliciesManager


class SiteConfiguration(SingletonModel):
    # Legal requirement of GDPR Article 8(1): [...] in relation to the offer
    # of information society services directly to a child, the processing of
    # the personal data of a child shall be lawful where the child is at least
    # 16 years old.
    USER_MIN_AGE = 16

    site_name = models.CharField(
        _("site name"),
        max_length=30, default='Pasporta Servo')

    salt = models.CharField(
        _("encryption salt"),
        max_length=30, default='salo',
        help_text=_("Salt used for encoded unique links. Change it to invalidate all links."))

    token_max_age = models.PositiveIntegerField(
        _("unique link lifetime"),
        default=3600 * 24 * 2,
        help_text=_("In seconds: 2 days = 3600 x 24 x 2 = 172800"))

    host_min_age = models.PositiveSmallIntegerField(
        _("minumum age for hosting"),
        default=17,
        validators=[MinValueValidator(USER_MIN_AGE)])

    meet_min_age = models.PositiveSmallIntegerField(
        _("minumum age for meeting"),
        default=16,
        validators=[MinValueValidator(USER_MIN_AGE)])

    confirmation_validity_period = models.DurationField(
        _("confirmation validity period"),
        default=timedelta(weeks=42),
        help_text=_("Delay (in days/hours) after which an object is no longer considered as confirmed."))

    google_analytics_key = models.CharField(
        max_length=13, default='UA-99737795-1', blank=True)

    opencage_api_key = models.CharField(
        max_length=32, default='a27f7e361bdfe11881a987a6e86fb5fd', blank=True)

    # https://openmaptiles.com/hosting/
    openmaptiles_api_key = models.CharField(
        max_length=32, default='iQbjILhp2gs0dgNfTlIV', blank=True)

    def __str__(self):  # pragma: no cover
        return str(_("Site Configuration"))

    class Meta:
        verbose_name = _("Site Configuration")


class Policy(FlatPage):
    EFFECTIVE_DATE_PATTERN = r'^{#\s+([0-9-]+)\s+'
    EFFECTIVE_DATE_FORMAT = '%Y-%m-%d'

    objects = PoliciesManager()

    class Meta:
        proxy = True

    @cached_property
    def effective_date(self):
        return self.get_effective_date_for_policy(self.content)

    @classmethod
    def get_effective_date_for_policy(cls, policy_content):
        try:
            date = re.match(cls.EFFECTIVE_DATE_PATTERN, policy_content).group(1)
            return datetime.strptime(date, cls.EFFECTIVE_DATE_FORMAT).date()
        except AttributeError:
            warnings.warn("Policy does not indicate a date it takes effect on!")
            return None
        except ValueError as err:
            warnings.warn("Policy effective date '{}' is invalid; {}".format(date, err))
            return None


class Agreement(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"),
        related_name='+', on_delete=models.CASCADE)
    policy_version = models.CharField(
        _("version of policy"),
        max_length=50)
    withdrawn = models.DateTimeField(
        _("withdrawn on"),
        default=None, blank=True, null=True)

    class Meta:
        verbose_name = _("agreement")
        verbose_name_plural = _("agreements")
        default_permissions = ('delete', )
        unique_together = ('user', 'policy_version', 'withdrawn')

    def __str__(self):
        # xgettext:python-brace-format
        return str(_("User {user} agreed to '{policy}' on {date:%Y-%m-%d}")).format(
            user=self.user,
            policy=self.policy_version,
            date=self.created
        )
