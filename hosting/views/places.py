import decimal
import logging
import re
from collections import namedtuple
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.core.mail import send_mail
from django.http import (
    HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict,
)
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from braces.views import FormInvalidMessageMixin

from core.auth import ANONYMOUS, OWNER, PERM_SUPERVISOR, SUPERVISOR, AuthMixin
from core.forms import UserRegistrationForm
from core.models import SiteConfiguration
from core.templatetags.utils import next_link
from core.utils import sanitize_next
from maps import COUNTRIES_WITH_MANDATORY_REGION, SRID
from maps.utils import bufferize_country_boundaries

from ..forms import (
    PlaceBlockForm, PlaceBlockQuickForm, PlaceCreateForm, PlaceForm,
    PlaceLocationForm, UserAuthorizedOnceForm, UserAuthorizeForm,
)
from ..models import LOCATION_CITY, Place, Profile, Whereabouts
from .mixins import (
    CreateMixin, DeleteMixin, PlaceMixin, PlaceModifyMixin,
    ProfileIsUserMixin, ProfileModifyMixin, UpdateMixin,
)

User = get_user_model()


class PlaceCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, PlaceModifyMixin, FormInvalidMessageMixin,
        generic.CreateView):
    model = Place
    form_class = PlaceCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs


class PlaceUpdateView(
        UpdateMixin, AuthMixin, PlaceMixin, ProfileModifyMixin, PlaceModifyMixin, FormInvalidMessageMixin,
        generic.UpdateView):
    form_class = PlaceForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")


class PlaceLocationUpdateView(
        UpdateMixin, AuthMixin, PlaceMixin,
        generic.UpdateView):
    form_class = PlaceLocationForm
    update_partial = True

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('place_detail_verbose', kwargs={'pk': self.object.pk})


class PlaceDeleteView(
        DeleteMixin, AuthMixin, PlaceMixin, ProfileModifyMixin,
        generic.DeleteView):
    pass


class PlaceDetailView(AuthMixin, PlaceMixin, generic.DetailView):
    """
    Details about a place; allows also anonymous (unauthenticated) user access.
    For such users, the registration form will be displayed.
    """
    minimum_role = ANONYMOUS
    verbose_view = False

    def get_queryset(self):
        related = ['owner', 'owner__user', 'visibility', 'family_members_visibility', 'owner__email_visibility']
        qs = super().get_queryset().select_related(*related)
        if self.request.user.has_perm(PERM_SUPERVISOR):
            qs = qs.select_related('checked_by', 'checked_by__profile')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner_phones'] = self.object.owner.phones.filter(deleted=False).select_related('visibility')
        context['register_form'] = UserRegistrationForm
        context['place_location'] = self.calculate_position()
        context['blocking'] = self.calculate_blocking(self.object)
        context['simple_map'] = self.request.COOKIES.get('maptype') == '0'
        return context

    def calculate_position(self):
        place = self.object
        is_authenticated = self.request.user.is_authenticated

        location, location_box = None, None
        bounds = None

        def location_enclose(loc):
            if not loc or loc.empty:
                return None
            lat_buffer = 0.002 if -70 <= loc.y <= 70 else 0.001
            precision = decimal.Decimal('0.001')  # Three decimal places.
            return list(
                (
                    decimal.Decimal(loc.y + dy).quantize(precision),
                    decimal.Decimal(loc.x + dx).quantize(precision)
                )
                for (dy, dx) in [
                    [+lat_buffer, +0.005], [+lat_buffer, +0.002], [+lat_buffer, -0.002], [+lat_buffer, -0.005],
                    [+0.000, +0.005], [+0.000, -0.005],
                    [-lat_buffer, -0.005], [-lat_buffer, -0.002], [-lat_buffer, +0.002], [-lat_buffer, +0.005],
                ]
            )

        def location_truncate(loc):
            return Point(round(loc.x, 2), round(loc.y, 3), srid=SRID) if loc and not loc.empty else None

        if place.available and is_authenticated:
            if self.verbose_view:
                location = place.location
                location_type = 'P'  # = Point.
            else:
                location = location_truncate(place.location)
                location_box = location_enclose(location)
                location_type = 'C'  # = Circle.
        elif place.owner_available and is_authenticated:
            if self.verbose_view and place.location and place.location_confidence >= 8:
                location = location_truncate(place.location)
                location_box = location_enclose(location)
                location_type = 'C'  # = Circle.

        if (location is None or location.empty) and is_authenticated:
            location_type = 'R'  # = Region.
            geocities = Whereabouts.objects.filter(
                type=LOCATION_CITY, name=place.city.upper(), country=place.country)
            if place.country in COUNTRIES_WITH_MANDATORY_REGION:
                geocities = geocities.filter(state=place.state_province.upper())
            try:
                city_location = geocities.get()
            except Whereabouts.DoesNotExist:
                pass
            else:
                bounds = [{'geom': city_location.center}, {'geom': city_location.bbox}]

        if location is None and bounds is None:
            location_type = 'R'  # = Region.
            if place.location and not place.location.empty and is_authenticated:
                bounds = [
                    {'geom': location_truncate(place.location)},
                ]
            else:
                coords = bufferize_country_boundaries(place.country)
                # Mapbox prefers the boundaries to be speficied in the southwest, northeast order.
                bounds = [
                    {'geom': Point(coords['center'], srid=SRID)},
                    {'geom': LineString(coords['bbox']['southwest'], coords['bbox']['northeast'], srid=SRID)},
                ]

        return {'coords': location, 'box': location_box, 'type': location_type, 'bounds': bounds}

    @staticmethod
    def calculate_blocking(place):
        block = {}
        today = date.today()
        if place.is_blocked:
            block['enabled'] = True
            if place.blocked_from and place.blocked_from > today:
                block['display_from'] = True
                block['format_from'] = "MONTH_DAY_FORMAT" if place.blocked_from.year == today.year else "DATE_FORMAT"
            if place.blocked_until and place.blocked_until >= today:
                block['display_until'] = True
                block['format_until'] = "MONTH_DAY_FORMAT" if place.blocked_until.year == today.year else "DATE_FORMAT"
        else:
            block['enabled'] = False
        block['form'] = PlaceBlockQuickForm(instance=place)
        return block

    def validate_access(self):
        if getattr(self, '_access_validated', None):
            return self._access_validated
        user = self.request.user
        place = self.object
        result = namedtuple('AccessConstraint', 'redirect, is_authorized, is_supervisor, is_family_member')
        auth_log = logging.getLogger('PasportaServo.auth')

        # Require the unauthenticated user to login in the following cases:
        #   - the place was deleted
        #   - place owner blocked unauth'd viewing
        #   - place is not visible to the public.
        if not user.is_authenticated:
            cases = [place.deleted, not place.owner.pref.public_listing, not place.visibility.visible_online_public]
            if any(cases):
                auth_log.debug("One of the conditions satisfied: "
                               "[deleted = %s, not accessible by visitors = %s, not accessible by users = %s]",
                               *cases)
                self._access_validated = result(self.handle_no_permission(), None, None, None)
                return self._access_validated

        is_authorized = user in place.authorized_users_cache(also_deleted=True, complete=False)
        is_supervisor = self.role >= SUPERVISOR
        is_family_member = getattr(user, 'profile', None) in place.family_members_cache()
        self.__dict__.setdefault('debug', {}).update(
            {'authorized': is_authorized, 'family member': is_family_member}
        )
        content_unavailable = False

        # Block access for regular authenticated users in the following cases:
        #   - the place was deleted
        #   - place is not visible to the public.
        if not is_supervisor and not self.role == OWNER:
            cases = [place.deleted, not place.visibility.visible_online_public]
            if any(cases):
                auth_log.debug("One of the conditions satisfied: "
                               "[deleted = %s, not accessible by users = %s]",
                               *cases)
                content_unavailable = True

        self._access_validated = result(content_unavailable, is_authorized, is_supervisor, is_family_member)
        return self._access_validated

    def get_template_names(self):
        if getattr(self, '_access_validated', None) and self._access_validated.redirect:
            return ['core/content_unavailable.html']
        else:
            return super().get_template_names()

    def render_to_response(self, context, **response_kwargs):
        barrier = self.validate_access()
        if barrier.redirect:
            if isinstance(barrier.redirect, HttpResponse):
                return barrier.redirect
            else:
                return super().render_to_response(
                    dict(context, object_name=self.object._meta.verbose_name), **response_kwargs
                )
        # Automatically redirect the user to the verbose view if permission granted (in authorized_users list).
        if barrier.is_authorized and not barrier.is_supervisor and not isinstance(self, PlaceDetailVerboseView):
            # We switch the class to avoid fetching all data again from the database,
            # because everything we need is already available here.
            # TODO: Combine the two views into one class.
            self.__class__ = PlaceDetailVerboseView
            return self.render_to_response(context, **response_kwargs)
        else:
            return super().render_to_response(context, **response_kwargs)

    def get_debug_data(self):
        return self.debug


class PlaceDetailVerboseView(PlaceDetailView):
    verbose_view = True

    def render_to_response(self, context, **response_kwargs):
        barrier = self.validate_access()
        if barrier.redirect:
            if isinstance(barrier.redirect, HttpResponse):
                return barrier.redirect
            else:
                return super().render_to_response(
                    dict(context, object_name=self.object._meta.verbose_name), **response_kwargs
                )
        # Automatically redirect the user to the scarce view if permission to details not granted.
        # Non-authenticated user is a special case: we will just show the login/registration snippet,
        # becase we don't want to disclose too much information about the viewing settings.
        cases = [
            self.role >= OWNER,
            not self.request.user.is_authenticated,
            barrier.is_authorized,
            barrier.is_family_member,
        ]
        if any(cases):
            return super().render_to_response(context, **response_kwargs)
        else:
            return HttpResponseRedirect(reverse_lazy('place_detail', kwargs={'pk': self.kwargs['pk']}))


class PlaceBlockView(AuthMixin, PlaceMixin, generic.UpdateView):
    http_method_names = ['get', 'post', 'put']
    template_name = 'hosting/place_block_form.html'
    form_class = PlaceBlockForm
    exact_role = OWNER

    def get_permission_denied_message(self, *args, **kwargs):
        return _("Only the owner of the place can access this page")

    def get_success_url(self, *args, **kwargs):
        return self.get_redirect_url() or super().get_success_url(*args, **kwargs)

    def get_redirect_url(self):
        return sanitize_next(self.request)

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PlaceBlockQuickForm(data=QueryDict(request.body), instance=self.object)
        data_correct = form.is_valid()
        response = {'result': data_correct}
        if data_correct:
            form.save()
        else:
            response.update({'err': form.errors})
        return JsonResponse(response)


class UserAuthorizeView(AuthMixin, generic.FormView):
    """
    Form view to add a user to the list of authorized users for a place,
    to be able to see the complete details.
    """
    template_name = 'hosting/place_authorized_users.html'
    form_class = UserAuthorizeForm
    exact_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place, pk=self.kwargs['pk'])
        kwargs['auth_base'] = self.place
        return super().dispatch(request, *args, **kwargs)

    def get_permission_denied_message(self, *args, **kwargs):
        return _("Only the owner of the place can access this page")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        m = valid_back_link = re.match(
            r'^/([a-zA-Z]+)/(?:\d+/[\w-]+/([a-zA-Z]+)/)?',
            self.request.GET.get(settings.REDIRECT_FIELD_NAME, default='')
        )
        if valid_back_link:
            context['back_to'] = m.group(1).lower() if not m.group(2) else m.group(2).lower()

        def order_by_name(user):
            try:
                return (" ".join((user.profile.first_name, user.profile.last_name)).strip()
                        or user.username).lower()
            except Profile.DoesNotExist:
                return user.username.lower()

        context['authorized_set'] = [
            (user, UserAuthorizedOnceForm(initial={'user': user.pk}, auto_id=False))
            for user
            in sorted(self.place.authorized_users_cache(also_deleted=True), key=order_by_name)
        ]
        return context

    def form_valid(self, form):
        if not form.cleaned_data['remove']:
            # For addition, "user" is the username.
            user = get_object_or_404(User, username=form.cleaned_data['user'])
            if user not in self.place.authorized_users_cache(also_deleted=True):
                self.place.authorized_users.add(user)
                if not user.email.startswith(settings.INVALID_PREFIX):
                    self.send_email(user, self.place)
        else:
            # For removal, "user" is the primary key.
            user = get_object_or_404(User, pk=form.cleaned_data['user'])
            self.place.authorized_users.remove(user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        success_url = reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return format_lazy('{}?{}', success_url, next_link(self.request, redirect_to))
        return success_url

    def send_email(self, user, place):
        config = SiteConfiguration.get_solo()
        subject = _("[Pasporta Servo] You received an Authorization")
        email_template_text = get_template('email/new_authorization.txt')
        email_template_html = get_template('email/new_authorization.html')
        email_context = {
            'site_name': config.site_name,
            'user': user,
            'place': place,
        }
        send_mail(
            subject,
            email_template_text.render(email_context),
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=email_template_html.render(email_context),
            fail_silently=False,
        )
