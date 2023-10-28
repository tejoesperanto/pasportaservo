from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.contrib.sessions.models import Session
from django.utils import timezone

from .models import Product, Reservation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created')
    list_filter = ()
    search_fields = ()
    date_hierarchy = 'created'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # A new product is added to the list. Should update the flags in the sessions
            # of logged in users, for them to get the update...
            logged_in_users = (
                s for s in Session.objects.exclude(expire_date__lte=timezone.now())
                if s.get_decoded().get('_auth_user_id')
            )
            SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
            flag = 'flag_book_reservation'
            for session_key in (s.session_key for s in logged_in_users if flag in s.get_decoded()):
                s = SessionStore(session_key=session_key)
                del s[flag]
                s.save()


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'discount', 'support', 'product', 'created')
    list_display_links = ('user', 'amount')
    list_filter = ('product',)
    search_fields = ()
    date_hierarchy = 'created'
    raw_id_fields = ('user',)
