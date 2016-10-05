from django.db import models


class NotDeletedManager(models.Manager):
    def get_queryset(self):
        return super(NotDeletedManager, self).get_queryset().exclude(deleted=True)


class WithCoordManager(NotDeletedManager):
    def get_queryset(self):
        return super(WithCoordManager, self).get_queryset().filter(
            latitude__isnull=False,
            longitude__isnull=False,
            available=True,
        )
