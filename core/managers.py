from django.db import models
from django.db.models import functions as dbf


class PoliciesManager(models.Manager):
    """ Adds the 'policy_version' calculated field. """

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(url__startswith='/privacy-policy-')
            .annotate(
                version=dbf.Substr(  # Poor man's regex ^/privacy-policy-(.+)/$
                    dbf.Substr('url', 1, dbf.Length('url') - 1, output_field=models.CharField()),
                    len('/privacy-policy-') + 1)
            )
        )
