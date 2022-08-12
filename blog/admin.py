from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'content', 'pub_date', 'published']
    fields = (
        ('title', 'slug', 'author'),
        'content',
        'body',
        'description',
        'pub_date',
    )
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('body', 'description',)
    date_hierarchy = 'created'

    def published(self, obj):
        return obj.published
    published.short_description = _("Published")
    published.admin_order_field = 'pub_date'
    published.boolean = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'author':
            kwargs['queryset'] = get_user_model().objects.filter(username=request.user.username)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.readonly_fields + ('author',)
        return self.readonly_fields

    def add_view(self, request, form_url="", extra_context=None):
        data = request.GET.copy()
        data['author'] = request.user
        request.GET = data
        return super().add_view(request, form_url="", extra_context=extra_context)
