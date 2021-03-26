from functools import lru_cache

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.utils import display_for_value
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.flatpages.models import FlatPage
# from django.contrib.gis import admin as gis_admin
from django.contrib.gis.db.models import LineStringField, PointField
from django.contrib.gis.forms import OSMWidget
from django.db import models
from django.db.models import Q, Value as V, functions as dbf
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from django_countries.fields import Country

from core.models import Agreement
from maps.widgets import AdminMapboxGlWidget

from ..models import (
    Condition, ContactPreference, CountryRegion, Phone, Place, Preferences,
    Profile, TravelAdvice, VisibilitySettings, Website, Whereabouts,
)
from .filters import (
    ActiveStatusFilter, CountryMentionedOnlyFilter,
    EmailValidityFilter, PlaceHasLocationFilter,
    ProfileHasUserFilter, SupervisorFilter, VisibilityTargetFilter,
)
from .forms import WhereaboutsAdminForm
from .mixins import ShowConfirmedMixin, ShowCountryMixin, ShowDeletedMixin
from .widgets import AdminImageWithPreviewWidget

admin.site.index_template = 'admin/custom_index.html'
admin.site.disable_action('delete_selected')

admin.site.unregister(User)
admin.site.unregister(Group)


class PlaceInLine(ShowConfirmedMixin, ShowDeletedMixin, admin.StackedInline):
    model = Place
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        'country', 'state_province', ('city', 'closest_city'), 'postcode', 'address',
        'description', 'short_description',
        ('max_guest', 'max_night', 'contact_before'), 'conditions',
        'available', 'in_book', ('tour_guide', 'have_a_drink'), 'sporadic_presence',
        'display_confirmed', 'is_deleted',
    )
    raw_id_fields = ('owner', 'family_members', 'authorized_users',)
    readonly_fields = ('display_confirmed', 'is_deleted',)
    fk_name = 'owner'
    classes = ('collapse',)


class PhoneInLine(ShowDeletedMixin, admin.TabularInline):
    model = Phone
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ('number', 'country', 'type', 'comments', 'confirmed_on', 'is_deleted')
    readonly_fields = ('confirmed_on', 'is_deleted',)
    fk_name = 'profile'


class VisibilityInLine(GenericTabularInline):
    model = VisibilitySettings
    extra = 0
    can_delete = False
    fields = ('visible_online_public', 'visible_online_authed', 'visible_in_book', 'id')
    ct_fk_field = 'model_id'

    def get_readonly_fields(self, request, obj=None):
        return self.fields

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PreferencesInLine(admin.StackedInline):
    model = Preferences
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'email', 'password_algorithm', 'profile_link',
        'is_active', 'is_supervisor', 'last_login', 'date_joined',
        'is_staff', 'is_superuser',
    )
    list_display_links = ('id', 'username')
    list_select_related = ('profile',)
    list_filter = (
        SupervisorFilter, 'is_active', 'is_staff', 'is_superuser', EmailValidityFilter,
        ('groups', admin.RelatedOnlyFieldListFilter),
    )
    date_hierarchy = 'date_joined'

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Supervisors'), {'fields': ('groups',)}),
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
            return '[ - ]'
    profile_link.short_description = _("profile")

    def is_supervisor(self, obj):
        value = any(g for g in obj.groups.all() if len(g.name) == 2)
        return display_for_value(value, None, boolean=True)
    is_supervisor.short_description = _("supervisor status")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups')

    def get_field_queryset(self, db, db_field, request):
        if db_field.name == 'groups':
            return CustomGroupAdmin.CountryGroup.objects
        return super().get_field_queryset(db, db_field, request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Group)
class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'country', 'supervisors')
    list_per_page = 50

    def country(self, obj):
        return Country(obj.name).name if len(obj.name) == 2 else "-"
    country.short_description = _("country")

    def supervisors(self, obj):
        def get_formatted_list():
            for u in obj.user_set.all():
                link = reverse('admin:auth_user_change', args=[u.pk])
                account_link = '<a href="{url}">{username}</a>'.format(url=link, username=u)
                is_deleted = not u.is_active
                try:
                    profile_link = '<sup>(<a href="{url}">{name}</a>)</sup>'.format(
                        url=u.profile.get_admin_url(), name=_("profile"))
                except Profile.DoesNotExist:
                    profile_link = ''
                else:
                    is_deleted = is_deleted or u.profile.deleted_on
                indicator = '<span style="color:#dd4646">&#x2718;!</span>' if is_deleted else ''
                yield " ".join([indicator, account_link, profile_link])
        return format_html(", ".join(get_formatted_list())) if len(obj.name) == 2 else "-"
    supervisors.short_description = _("Supervisors")

    class CountryGroup(Group):
        class Meta:
            proxy = True
            permissions = (
                ("can_supervise", "Can modify users from specific country"),
            )

        def __str__(self):
            if len(self.name) != 2:
                return self.name
            return format_html('{country_code}&emsp;&ndash;&ensp;{country_name}',
                               country_code=self.name, country_name=Country(self.name).name)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('user_set__profile')


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'policy_link', 'user_link', 'created', 'modified', 'withdrawn',
    )
    ordering = ('-policy_version', '-modified', 'user__username')
    search_fields = ('user__username',)
    list_filter = ('policy_version',)
    date_hierarchy = 'created'
    fields = (
        'user_link', 'policy_link',
        'created', 'modified', 'withdrawn',
    )
    readonly_fields = [f.name for f in Agreement._meta.fields] + ['user_link', 'policy_link']

    def user_link(self, obj):
        try:
            link = reverse('admin:auth_user_change', args=[obj.user.pk])
            account_link = f'<a href="{link}">{obj.user}</a>'
            try:
                profile_link = '&nbsp;(<a href="{url}">{name}</a>)</sup>'.format(
                    url=obj.user.profile.get_admin_url(), name=_("profile"))
            except Profile.DoesNotExist:
                profile_link = ''
            return format_html(" ".join([account_link, profile_link]))
        except AttributeError:
            return format_html('{userid} <sup>?</sup>', userid=obj.user_id)
    user_link.short_description = _("user")
    user_link.admin_order_field = 'user__username'

    def policy_link(self, obj):
        try:
            cache = self._policies_cache
        except AttributeError:
            cache = self._policies_cache = {}
        if obj.policy_version in cache:
            return cache[obj.policy_version]
        try:
            policy = (
                FlatPage.objects
                .values_list('id', flat=True)
                .get(url='/privacy-policy-{}/'.format(obj.policy_version)))
            link = reverse('admin:flatpages_flatpage_change', args=[policy])
            value = format_html('<a href="{url}">{policy}</a>', url=link, policy=obj.policy_version)
        except FlatPage.DoesNotExist:
            value = obj.policy_version
        finally:
            cache[obj.policy_version] = value
            return value
    policy_link.short_description = _("version of policy")
    policy_link.admin_order_field = 'policy_version'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'user__profile')
        qs = qs.only(
                *[f.name for f in Agreement._meta.fields],
                'user__id', 'user__username', 'user__profile__id')
        return qs

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method != 'POST'


class TrackingModelAdmin(ShowConfirmedMixin):
    fields = (
        ('checked_on', 'checked_by'), 'display_confirmed', 'deleted_on',
    )
    readonly_fields = ('display_confirmed',)

    class InstanceApprover(User):
        class Meta:
            proxy = True

        def __str__(self):
            try:
                fullname = " : ".join([self.username, str(self.profile)])
            except Profile.DoesNotExist:
                fullname = self.username
            return " ".join([fullname, "[N/A]" if not self.is_active else ""])

    def get_field_queryset(self, db, db_field, request):
        if db_field.name == 'checked_by':
            return (self.InstanceApprover.objects
                    .filter(Q(is_superuser=True) | Q(groups__name__regex=r'[A-Z]{2}'))
                    .distinct()
                    .select_related('profile').defer('profile__description')
                    .order_by('username'))
        return super().get_field_queryset(db, db_field, request)


@admin.register(VisibilitySettings)
class VisibilityAdmin(admin.ModelAdmin):
    visibility_fields = tuple(
        f.name for f in VisibilitySettings._meta.get_fields()
        if f.name.startswith(VisibilitySettings._PREFIX)
    )
    list_display = (
        'id', '__str__', 'content_object_link',
    ) + visibility_fields
    list_display_links = ('id', '__str__')
    search_fields = ('id', 'model_id')
    list_filter = (
        VisibilityTargetFilter,
        'visible_in_book', 'visible_online_authed', 'visible_online_public',
    )
    fields = (
        'model_type', 'content_object_link', 'content_type',
    ) + visibility_fields
    readonly_fields = fields

    def content_object_link(self, obj):
        try:
            link = reverse('admin:{content.app_label}_{content.model}_change'.format(content=obj.content_type),
                           args=[obj.model_id])
            return format_html(
                '{pk}: <a href="{url}">{content}</a>',
                url=link,
                pk=obj.content_object.pk, content=obj.content_object
            )
        except AttributeError:
            return '-'
    content_object_link.short_description = _("object")
    content_object_link.admin_order_field = 'model_id'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content_object')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Profile)
class ProfileAdmin(TrackingModelAdmin, ShowDeletedMixin, admin.ModelAdmin):
    list_display = (
        'id', '__str__', 'title', 'first_name', 'last_name',
        'birth_date',
        'user__email', 'user_link',
        'confirmed_on', 'checked_by__name', 'is_deleted', 'modified',
    )
    list_display_links = ('id', '__str__')
    search_fields = (
        'id', 'first_name', 'last_name', 'user__email', 'user__username',
    )
    list_filter = (
        'confirmed_on', 'checked_on', 'deleted_on',
        EmailValidityFilter, ProfileHasUserFilter, 'death_date',
    )
    date_hierarchy = 'birth_date'

    fieldsets = (
        (None, {'fields': (
            'user', 'title', 'first_name', 'last_name', 'names_inversed',
            'birth_date', 'death_date',
            ('gender', 'pronoun'),
            'description', 'avatar', 'email',
        )}),
        (_('Supervisors'), {'fields': ('supervisor',)}),
        (_('Important dates'), {'fields': TrackingModelAdmin.fields}),
    )
    fields = None
    raw_id_fields = ('user',)
    radio_fields = {'title': admin.HORIZONTAL}
    readonly_fields = ('supervisor',) + TrackingModelAdmin.readonly_fields
    formfield_overrides = {
        models.ImageField: {'widget': AdminImageWithPreviewWidget},
    }

    inlines = [VisibilityInLine, PreferencesInLine, PlaceInLine, PhoneInLine]

    def user__email(self, obj):
        try:
            return obj.user.email
        except AttributeError:
            return '-'
    user__email.short_description = _("email address")
    user__email.admin_order_field = 'user__email'

    def user_link(self, obj):
        try:
            link = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html('<a href="{url}">{username}</a>', url=link, username=obj.user)
        except AttributeError:
            return '-'
    user_link.short_description = _("user")
    user_link.admin_order_field = 'user__username'

    def checked_by__name(self, obj):
        try:
            return obj.checked_by.username
        except AttributeError:
            return '-'
    checked_by__name.short_description = _("approved by")
    checked_by__name.admin_order_field = 'checked_by__username'

    def supervisor(self, obj):
        country_list = CustomGroupAdmin.CountryGroup.objects.filter(
            name__regex=r'^[A-Z]{2}$',
            user__pk=obj.user_id if obj.user_id else -1)
        if country_list:
            return format_html(',&nbsp; '.join(map(str, country_list)))
        else:
            return self.get_empty_value_display()
    supervisor.short_description = _("supervisor status")

    def get_list_display(self, request):
        death_date_filter = lambda param: (
            param == 'death_date'
            or (param.startswith('death_date')
                and not (param == 'death_date__isnull' and request.GET[param] == 'True'))
        )
        if any(filter(death_date_filter, request.GET.keys())):
            birth_date_field_index = self.list_display.index('birth_date')
            return (
                self.list_display[:birth_date_field_index + 1]
                + ('death_date',)
                + self.list_display[birth_date_field_index + 1:]
            )
        return self.list_display

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'checked_by')


@admin.register(Place)
class PlaceAdmin(TrackingModelAdmin, ShowCountryMixin, ShowDeletedMixin, admin.ModelAdmin):
    list_display = (
        'id', 'city', 'postcode', 'state_province', 'display_country',
        'display_location',
        # 'max_host', 'max_night', 'contact_before',
        'available', 'in_book',
        'owner_link',
        'confirmed_on', 'checked_by__name', 'is_deleted', 'modified',
    )
    list_display_links = (
        'id', 'city', 'state_province', 'display_country',
    )
    search_fields = (
        'address', 'city', 'postcode', 'country', 'state_province',
        'owner__first_name', 'owner__last_name', 'owner__user__email',
    )
    list_filter = (
        'confirmed_on', 'checked_on', 'in_book', 'available', PlaceHasLocationFilter, 'deleted_on',
        CountryMentionedOnlyFilter,
    )

    fieldsets = (
        (None, {'fields': (
            'owner',
            'country', 'state_province', ('city', 'closest_city'), 'postcode', 'address',
            'location',
        )}),
        (_('Conditions'), {'fields': (
            'description', 'short_description',
            ('max_guest', 'max_night', 'contact_before'), 'conditions',
            'available', 'in_book', ('tour_guide', 'have_a_drink'), 'sporadic_presence',
            'family_members',
        )}),
        (_('Permissions'), {'fields': ('authorized_users',)}),
        (_('Important dates'), {'fields': TrackingModelAdmin.fields}),
    )
    fields = None
    formfield_overrides = {
        PointField: {'widget': AdminMapboxGlWidget},
    }
    raw_id_fields = ('owner', 'authorized_users',)
    filter_horizontal = ('family_members',)

    inlines = [VisibilityInLine, ]

    def display_location(self, obj):
        return (
            ' '.join([
                '{point.y:.4f} {point.x:.4f}'.format(point=obj.location),
                '{symbol}{precision}'.format(
                    symbol=chr(8982), precision=obj.location_confidence or 0)
            ]) if obj.location
            else None
        )
    display_location.short_description = _("location")

    def owner_link(self, obj):
        return format_html('<a href="{url}">{name}</a>', url=obj.owner.get_admin_url(), name=obj.owner)
    owner_link.short_description = _("owner")
    owner_link.admin_order_field = dbf.Concat(
        'owner__first_name', V(","), 'owner__last_name', V(","), 'owner__user__username'
    )

    def checked_by__name(self, obj):
        try:
            return obj.checked_by.username
        except AttributeError:
            return '-'
    checked_by__name.short_description = _("approved by")
    checked_by__name.admin_order_field = 'checked_by__username'

    class FamilyMember(Profile):
        class Meta:
            ordering = ['first_name', 'last_name', 'id']
            proxy = True

        def __str__(self):
            return "(p:%05d, u:%05d) %s" % (self.pk,
                                            self.user_id if self.user_id else 0,
                                            super().__str__())

    @lru_cache(maxsize=None)
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('owner__user', 'checked_by')
        qs = qs.defer('owner__description')
        try:
            if not self.single_object_view:
                qs = qs.defer('description', 'short_description', 'address')
        except Exception:
            pass
        return qs

    def get_field_queryset(self, db, db_field, request):
        if db_field.name == 'family_members':
            return PlaceAdmin.FamilyMember.objects.select_related('user')
        return super().get_field_queryset(db, db_field, request)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.single_object_view = True
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        self.single_object_view = True
        return super().add_view(
            request, form_url=form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        self.single_object_view = False
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Phone)
class PhoneAdmin(TrackingModelAdmin, ShowCountryMixin, ShowDeletedMixin, admin.ModelAdmin):
    list_display = ('number_intl', 'profile_link', 'country_code', 'display_country', 'type', 'is_deleted')
    list_select_related = ('profile__user',)
    search_fields = ('number', 'country', 'profile__first_name', 'profile__last_name')
    list_filter = ('type', 'deleted_on', CountryMentionedOnlyFilter)

    fieldsets = (
        (None, {'fields': ('profile', 'number', 'country', 'type', 'comments',)}),
        (_('Important dates'), {'fields': TrackingModelAdmin.fields}),
    )
    fields = None
    raw_id_fields = ('profile',)
    radio_fields = {'type': admin.VERTICAL}
    inlines = [VisibilityInLine, ]

    def number_intl(self, obj):
        return obj.number.as_international
    number_intl.short_description = _("number")
    number_intl.admin_order_field = 'number'

    def profile_link(self, obj):
        return format_html('<a href="{url}">{name}</a>', url=obj.profile.get_admin_url(), name=obj.profile)
    profile_link.short_description = _("profile")
    profile_link.admin_order_field = dbf.Concat(
        'profile__first_name', V(","), 'profile__last_name', V(","), 'profile__user__username'
    )

    def country_code(self, obj):
        return obj.number.country_code
    country_code.short_description = _("country code")


@admin.register(CountryRegion)
class CountryRegionAdmin(ShowCountryMixin, admin.ModelAdmin):
    list_display = (
        'display_country', 'iso_code',
        'latin_code', 'latin_name', 'local_code', 'local_name', 'esperanto_name',
    )
    list_display_links = ('display_country', 'iso_code')
    list_filter = (
        CountryMentionedOnlyFilter,
    )
    list_editable = ('esperanto_name',)
    ordering = ('country', 'iso_code', 'id')


@admin.register(Whereabouts)
class WhereaboutsAdmin(ShowCountryMixin, admin.ModelAdmin):
    list_display = ('name', 'state', 'display_country', 'type')
    search_fields = ('name', 'state')
    list_filter = (
        'type', CountryMentionedOnlyFilter,
    )
    form = WhereaboutsAdminForm
    fields = ('type', 'name', 'state', 'country', 'bbox')
    formfield_overrides = {
        LineStringField: {'widget': OSMWidget},
    }


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbr')
    prepopulated_fields = {'slug': ("name",)}

    fields = ('name', 'abbr', 'slug', 'icon')

    def icon(self, obj):
        return format_html('<img src="{static}img/cond_{slug}.svg" style="width:4ex; height:4ex;"/>',
                           static=settings.STATIC_URL, slug=obj.slug)
    icon.short_description = _("image")

    def add_view(self, request, form_url='', extra_context=None):
        self.readonly_fields = ()
        return super().add_view(
            request, form_url=form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.readonly_fields = ('icon',)
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context)


@admin.register(Website)
class WebsiteAdmin(TrackingModelAdmin, admin.ModelAdmin):
    list_display = ('url', 'profile')
    search_fields = (
        'url',
        'profile__first_name', 'profile__last_name', 'profile__user__email', 'profile__user__username',
    )
    fields = ('profile', 'url') + TrackingModelAdmin.fields
    raw_id_fields = ('profile',)


@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    pass


@admin.register(TravelAdvice)
class TravelAdviceAdmin(admin.ModelAdmin):
    list_display = ('advice', 'countries_list', 'active_status', 'active_from', 'active_until')
    list_filter = (
        ActiveStatusFilter,
        CountryMentionedOnlyFilter,
    )
    date_hierarchy = 'active_until'
    fields = (
        ('active_from', 'active_until'),
        'content', 'description', 'countries',
    )
    readonly_fields = ('description',)
    save_as = True
    save_as_continue = False

    def advice(self, obj):
        return obj.trimmed_content()
    advice.short_description = _("travel advice")
    advice.admin_order_field = 'content'

    def countries_list(self, obj):
        return obj.applicable_countries(code=False)
    countries_list.short_description = _("countries")

    def active_status(self, obj):
        # The status is a calculated field (QuerySet annotation).
        return obj.is_active
    active_status.short_description = _("active")
    active_status.admin_order_field = 'is_active'
    active_status.boolean = True
