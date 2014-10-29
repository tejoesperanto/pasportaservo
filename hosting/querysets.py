from django.db import models


class BaseQuerySet(models.QuerySet):
    def all(self):
        return self.filter(deleted=False)
