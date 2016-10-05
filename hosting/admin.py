from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.core import urlresolvers
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin

from .models import Profile, Place, Phone, Condition, Website, ContactPreference


admin.site.disable_action('delete_selected')

# admin.site.unregister(Group)
admin.site.unregister(User)


class PlaceInLine(admin.StackedInline):
    model = Place
    extra = 0
    can_delete = False
    fields = (
        'owner', 'country', 'state_province', ('city', 'closest_city'), 'postcode', 'address',
        ('latitude', 'longitude'),
        'description', 'short_description',
        ('max_guest', 'max_night', 'contact_before'), 'conditions',
        'available', 'in_book', ('tour_guide', 'have_a_drink'), 'sporadic_presence',
        'family_members', 'authorized_users',
        ('checked', 'checked_by'), 'confirmed', 'deleted',
    )
    raw_id_fields = ('owner', 'authorized_users', 'checked_by')
    filter_horizontal = ('family_members',)
    fk_name = 'owner'
    classes = ('collapse',)


class PhoneInLine(admin.TabularInline):
    model = Phone
    extra = 0
    can_delete = False
    fk_name = 'profile'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'email', 'password_algorithm', 'profile_link',
        'last_login', 'date_joined',
        'is_active', 'is_staff', 'is_superuser',
    )
    list_display_links = ('id', 'username')
    date_hierarchy = 'date_joined'

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined',)

    def password_algorithm(self, obj):
        if len(obj.password) == 32:
            return _("MD5 (weak)")
        if obj.password[:13] == 'pbkdf2_sha256':
            return 'PBKDF2 SHA256'
    password_algorithm.short_description = _("Password algorithm")

    def profile_link(self, obj):
        try:
            fullname = obj.profile if (obj.profile.first_name or obj.profile.last_name) else "--."
            return format_html('<a href="{url}">{name}</a>', url=obj.profile.get_admin_url(), name=fullname)
        except AttributeError:
            return '-'
    profile_link.short_description = _("profile")
    profile_link.admin_order_field = 'profile'


class ProfileHasUserFilter(admin.SimpleListFilter):
    title = _("user is defined")
    parameter_name = 'has_user'

    def lookups(self, request, model_admin):
        return ((1, _('Yes')), (0, _('No')))

    def queryset(self, request, queryset):
        if str(self.value()).isdigit():
            return queryset.filter(user__isnull=(int(self.value()) == 0))


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 'title', 'first_name', 'last_name',
        'birth_date', #'avatar', 'description',
        'user__email', 'user_link',
        'confirmed', 'checked_by', 'deleted', 'modified',
    )
    search_fields = [
        'id', 'first_name', 'last_name', 'user__email', 'user__username',
    ]
    list_filter = (
        'confirmed', 'checked', 'deleted', ProfileHasUserFilter,
    )
    date_hierarchy = 'birth_date'
    raw_id_fields = ('user', 'checked_by')
    inlines = [PlaceInLine, PhoneInLine]

    def user__email(self, obj):
        try:
            return obj.user.email
        except AttributeError:
            return '-'
    user__email.short_description = _("Email")
    user__email.admin_order_field = 'user__email'

    def user_link(self, obj):
        try:
            link = urlresolvers.reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{url}">{username}</a>', url=link, username=obj.user)
        except AttributeError:
            return '-'
    user_link.short_description = _("user")
    user_link.admin_order_field = 'user'


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'city', 'postcode', 'state_province', 'country',
        'latitude', 'longitude',
        # 'max_host', 'max_night', 'contact_before',
        'available', 'in_book',
        'owner_link',
        'confirmed', 'checked_by', 'deleted', 'modified',
    )
    list_display_links = (
        'city', 'state_province', 'country',
        'latitude', 'longitude',
    )
    search_fields = [
        'address', 'city', 'postcode', 'country', 'state_province',
        'owner__first_name', 'owner__last_name', 'owner__user__email',
    ]
    list_filter = (
        'confirmed', 'checked', 'in_book', 'available', 'deleted',
        'country',
    )
    fields = (
        'owner', 'country', 'state_province', ('city', 'closest_city'), 'postcode', 'address',
        ('latitude', 'longitude'),
        'description', 'short_description',
        ('max_guest', 'max_night', 'contact_before'), 'conditions',
        'available', 'in_book', ('tour_guide', 'have_a_drink'), 'sporadic_presence',
        'family_members', 'authorized_users',
        ('checked', 'checked_by'), 'confirmed', 'deleted',
    )
    raw_id_fields = ('owner', 'authorized_users', 'checked_by')
    filter_horizontal = ('family_members',)

    def owner_link(self, obj):
        return format_html('<a href="{url}">{name}</a>', url=obj.owner.get_admin_url(), name=obj.owner)
    owner_link.short_description = _("owner")
    owner_link.admin_order_field = 'owner'


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number_intl', 'country_code', 'country', 'type')
    search_fields = ['number', 'country']
    list_filter = ('type', 'country')
    raw_id_fields = ('profile',)

    def number_intl(self, obj):
        return obj.number.as_international
    number_intl.short_description = _("number")
    number_intl.admin_order_field = 'number'

    def country_code(self, obj):
        return obj.number.country_code
    country_code.short_description = _("country code")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ("name",)}


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('url', 'profile')
    search_fields = [
        'url',
        'profile__first_name', 'profile__last_name', 'profile__user__email', 'profile__user__username',
    ]
    raw_id_fields = ('profile',)


@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    pass
