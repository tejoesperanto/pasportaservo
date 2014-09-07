from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from wpadmin.menu import menus, items
from .models import Profile, Place, Phone, Condition


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('title', '__unicode__', 'birth_date')


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'postcode', 'country', 'max_host', 'max_night', 'contact_before', 'booked', 'available', 'in_book')


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number', 'type')


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', )


admin.site.site_header = _("Pasporta Servo administration")


class CustomTopMenu(menus.DefaultTopMenu):
    """
    This class is added just for the custom title, based on site.site_header.
    We should be able to remove it in further version of wpadmin (>1.6.1).
    Check wpadmin.menu.menus.DefaultTopMenu.init_with_context()
    """

    def init_with_context(self, context):
        self.children += [
            items.MenuItem(
                title=admin.site.site_header,
                url=None,
                icon='fa-gears',
                css_styles='font-size: 1.5em;',
            ),
            items.UserTools(
                css_styles='float: right;',
                is_user_allowed=lambda user: user.is_active and user.is_staff,
            ),
        ]
