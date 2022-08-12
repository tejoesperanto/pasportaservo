import re

from django.conf import settings
from django.db import models
from django.db.models import BooleanField, Case, F, Q, When
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from commonmark import commonmark
from django_extensions.db.models import TimeStampedModel
from simplemde.fields import SimpleMDEField


class PublishedQueryset(models.QuerySet):
    def published(self):
        return self.filter(published=True)


class PublishedManager(models.Manager):
    def get_queryset(self):
        return PublishedQueryset(self.model, using=self._db).annotate(
            published=Case(
                When(pub_date__isnull=True, then=False),
                When(pub_date__gt=timezone.now(), then=False),
                default=True,
                output_field=BooleanField()
            ),
            has_more=Case(
                When(~Q(body=F('description')), then=True),
                default=False,
                output_field=BooleanField()
            ),
        )

    def published(self):
        return self.get_queryset().published()


class Post(TimeStampedModel):
    title = models.CharField(
        _("title"),
        max_length=200)
    slug = models.SlugField(
        _("slug"),
        unique=True)
    content = SimpleMDEField(
        _("Markdown content"),
        simplemde_options={
            'showIcons': ['heading-smaller', 'heading-bigger', 'horizontal-rule'],
            'spellChecker': False,
        })
    body = models.TextField(
        _("HTML content"),
        blank=True)
    description = models.TextField(
        _("HTML description"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("author"),
        blank=True, null=True, on_delete=models.SET_NULL)
    pub_date = models.DateTimeField(
        _("publication date"),
        null=True, blank=True)

    objects = PublishedManager()

    class Meta:
        ordering = ['-pub_date', '-created']
        verbose_name = _("post")
        verbose_name_plural = _("posts")

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<Post: {}>".format(self.slug)

    def get_absolute_url(self):
        return reverse_lazy('blog:post', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        content = re.split(r'(?<!-)----(?!-)', self.content, maxsplit=1)
        self.body = commonmark("".join(content))
        self.description = commonmark(content[0])
        return super().save(*args, **kwargs)
    save.alters_data = True
