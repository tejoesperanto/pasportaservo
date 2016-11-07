from django.db import models


class NotDeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=True)


class AvailablesManager(NotDeletedManager):
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class WithCoordManager(AvailablesManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
