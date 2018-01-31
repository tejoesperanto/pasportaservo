import json
import logging
import re
from collections import OrderedDict
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import Distance
from django.core import serializers
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import (
    Http404, HttpResponseBadRequest,
    HttpResponseRedirect, JsonResponse, QueryDict,
)
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.encoding import uri_to_iri
from django.utils.http import urlquote_plus
from django.utils.six.moves.urllib.parse import unquote_plus
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from braces.views import FormInvalidMessageMixin
from django_countries.fields import Country

from core.auth import (
    ANONYMOUS, OWNER, PERM_SUPERVISOR, SUPERVISOR, VISITOR, AuthMixin,
)
from core.forms import UserRegistrationForm
from core.mixins import LoginRequiredMixin
from core.models import SiteConfiguration

from .forms import *  # noqa: F403
from .mixins import *  # noqa: F403
from .models import Phone, Place, Profile, VisibilitySettings
from .utils import geocode

User = get_user_model()
lang = settings.LANGUAGE_CODE


class ProfileCreateView(
        LoginRequiredMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.CreateView):
    model = Profile
    form_class = ProfileCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def dispatch(self, request, *args, **kwargs):
        try:
            # Redirect to profile edit page if user is logged in & profile already exists.
            return HttpResponseRedirect(self.request.user.profile.get_edit_url(), status=301)
        except Profile.DoesNotExist:
            return super().dispatch(request, *args, **kwargs)
        except AttributeError:
            # Redirect to registration page when user is not authenticated.
            return HttpResponseRedirect(reverse_lazy('register'), status=303)

    def get_form(self, form_class=ProfileCreateForm):
        return form_class(user=self.request.user, **self.get_form_kwargs())


class ProfileUpdateView(
        UpdateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.UpdateView):
    model = Profile
    form_class = ProfileForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")


class ProfileDeleteView(
        DeleteMixin, AuthMixin, ProfileIsUserMixin,
        generic.DeleteView):
    model = Profile
    form_class = ProfileForm
    success_url = reverse_lazy('logout')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        return context

    def get_success_url(self):
        # Administrators will be redirected to the deleted profile's page.
        if self.role >= SUPERVISOR:
            return self.object.get_absolute_url()
        return self.success_url

    def get_failure_url(self):
        return reverse_lazy('profile_settings', kwargs={
            'pk': self.object.pk, 'slug': self.object.autoslug})

    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the profile and some associated objects,
        deactivate the linked user,
        and then redirect to the success URL.
        """
        now = timezone.now()
        self.object = self.get_object()
        if not self.object.deleted:
            for place in self.object.owned_places.filter(deleted=False):
                place.deleted_on = now
                place.save()
                place.family_members.filter(
                    deleted=False, user_id__isnull=True
                ).update(deleted_on=now)
            self.object.phones.filter(deleted=False).update(deleted_on=now)
            self.object.user.is_active = False
            self.object.user.save()
        if self.role == OWNER:
            messages.success(request, _("Farewell !"))
        return super().delete(request, *args, **kwargs)


class ProfileRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if kwargs.get('pk'):
            profile = get_object_or_404(Profile, pk=kwargs['pk'])
            if profile.user_id:
                return profile.get_absolute_url()
            else:
                raise Http404("Detached profile (probably a family member).")
        try:
            return self.request.user.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')


class ProfileDetailView(AuthMixin, ProfileIsUserMixin, generic.DetailView):
    model = Profile
    public_view = True
    minimum_role = VISITOR

    def get_queryset(self):
        return super().get_queryset().select_related('user')

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.deleted and self.role == VISITOR and not self.request.user.has_perm(PERM_SUPERVISOR):
            raise Http404("Profile was deleted.")
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False).prefetch_related('family_members')
        display_phones = self.object.phones.filter(deleted=False)
        context['phones'] = display_phones
        context['phones_public'] = display_phones.filter(visibility__visible_online_public=True)
        return context


class ProfileEditView(ProfileDetailView):
    template_name = 'hosting/profile_edit.html'
    public_view = False
    minimum_role = OWNER


class ProfileSettingsView(ProfileDetailView):
    template_name = 'hosting/settings.html'
    minimum_role = OWNER

    @property
    def profile_email_help_text(self):
        return Profile._meta.get_field('email').help_text

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['privacy_matrix'] = ProfilePrivacyUpdateView.VisibilityFormSet(
            profile=self.object, form_kwargs={'read_only': self.role > OWNER})
        return context


class ProfileSettingsRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            return reverse_lazy('profile_settings', kwargs={
                'pk': self.request.user.profile.pk, 'slug': self.request.user.profile.autoslug})
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')


class ProfileEmailUpdateView(AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, generic.UpdateView):
    model = Profile
    template_name = 'hosting/profile-email_form.html'
    form_class = ProfileEmailUpdateForm
    minimum_role = OWNER


class ProfilePrivacyUpdateView(AuthMixin, ProfileMixin, generic.View):
    http_method_names = ['post']
    exact_role = OWNER

    VisibilityFormSet = modelformset_factory(
        VisibilitySettings,
        form=VisibilityForm, formset=VisibilityFormSetBase, extra=0)

    def get_permission_denied_message(self, object, context_omitted=False):
        return _("Only the user themselves can access this page")

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        data = QueryDict(request.body)
        formset = self.VisibilityFormSet(profile=profile, data=data)
        data_correct = formset.is_valid()
        if data_correct:
            formset.save()
        else:
            for index, err in enumerate(formset.errors):
                err['_pk'] = formset[index].instance.pk
                if err:
                    err['_obj'] = repr(formset[index].instance)
            logging.getLogger('PasportaServo.{module_}.{class_}'.format(
                module_=__name__, class_=self.__class__.__name__
            )).error(formset.errors)

        if request.is_ajax():
            return JsonResponse({'result': data_correct})
        else:
            if not data_correct:
                raise ValueError("Unexpected visibility cofiguration. Ref {}".format(formset.errors))
            return HttpResponseRedirect('{}#pR'.format(profile.get_edit_url()))


class PlaceCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.CreateView):
    model = Place
    form_class = PlaceCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs


class PlaceUpdateView(
        UpdateMixin, AuthMixin, PlaceMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.UpdateView):
    form_class = PlaceForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def form_valid(self, form):
        response = super().form_valid(form)
        if '_gotomap' in self.request.POST or form.confidence < 8:
            map_url = reverse_lazy('place_location_update', kwargs={'pk': self.object.pk})
            return HttpResponseRedirect(map_url)
        return response


class PlaceLocationUpdateView(UpdateMixin, AuthMixin, PlaceMixin, generic.UpdateView):
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
    View with details about a place; allows also anonymous (unauthenticated) user access.
    For such users, the registration form will be displayed.
    """
    model = Place
    minimum_role = ANONYMOUS
    verbose_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner_phones'] = self.object.owner.phones.filter(deleted=False)
        context['register_form'] = UserRegistrationForm
        context['blocking'] = self.calculate_blocking(self.object)
        return context

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
        block['form'] = PlaceBlockForm(instance=place)
        return block

    def render_to_response(self, context, **response_kwargs):
        # Automatically redirect the user to the verbose view if permission granted (in authorized_users list).
        is_authorized = self.request.user in self.object.authorized_users_cache(also_deleted=True, complete=False)
        is_supervisor = self.role >= SUPERVISOR
        if is_authorized and not is_supervisor and not isinstance(self, PlaceDetailVerboseView):
            # We switch the class to avoid fetching all data again from the database,
            # because everything we need is already available here.
            # TODO: Combine the two views into one class.
            self.__class__ = PlaceDetailVerboseView
            return self.render_to_response(context, **response_kwargs)
        else:
            return super().render_to_response(context)


class PlaceDetailVerboseView(PlaceDetailView):
    verbose_view = True

    def render_to_response(self, context, **response_kwargs):
        # Automatically redirect the user to the scarce view if permission to details not granted.
        user = self.request.user
        is_authorized = user in self.object.authorized_users_cache(also_deleted=True, complete=False)
        is_family_member = getattr(user, 'profile', None) in self.object.family_members_cache()
        self.__dict__.setdefault('debug', {}).update(
            {'authorized': is_authorized, 'family member': is_family_member}
        )
        if self.role >= OWNER or is_authorized or is_family_member:
            return super().render_to_response(context)
        else:
            return HttpResponseRedirect(reverse_lazy('place_detail', kwargs={'pk': self.kwargs['pk']}))

    def get_debug_data(self):
        return self.debug


class PlaceBlockView(AuthMixin, PlaceMixin, generic.View):
    http_method_names = ['put']
    exact_role = OWNER

    def put(self, request, *args, **kwargs):
        place = self.get_object()
        if place.deleted:
            return JsonResponse({'result': False, 'err': {NON_FIELD_ERRORS: [_("Deleted place"), ]}})
        form = PlaceBlockForm(data=QueryDict(request.body), instance=place)
        data_correct = form.is_valid()
        viewresponse = {'result': data_correct}
        if data_correct:
            form.save()
        else:
            viewresponse.update({'err': form.errors})
        return JsonResponse(viewresponse)


class PhoneCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin,
        generic.CreateView):
    model = Phone
    form_class = PhoneCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs


class PhoneUpdateView(
        UpdateMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.UpdateView):
    form_class = PhoneForm


class PhoneDeleteView(
        DeleteMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.DeleteView):
    pass


class InfoConfirmView(LoginRequiredMixin, generic.View):
    """Allows the current user (only) to confirm their profile and accommodation details as up-to-date."""
    http_method_names = ['post']
    template_name = 'links/confirmed.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        try:
            request.user.profile.confirm_all_info()
        except Profile.DoesNotExist:
            if request.is_ajax():
                return HttpResponseBadRequest(
                    "Cannot confirm data; a profile must be created first.",
                    content_type="text/plain")
            else:
                return HttpResponseRedirect(reverse_lazy('profile_create'))
        else:
            if request.is_ajax():
                return JsonResponse({'success': 'confirmed'})
            else:
                return TemplateResponse(request, self.template_name)


class PlaceCheckView(AuthMixin, PlaceMixin, generic.View):
    """Allows a supervisor to confirm accommodation details of a user as up-to-date."""
    http_method_names = ['post']
    template_name = '404.html'
    minimum_role = SUPERVISOR

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        place = self.get_object()
        place_data = serializers.serialize('json', [place], fields=PlaceForm._meta.fields)
        place_data = json.loads(place_data)[0]['fields']
        owner_data = serializers.serialize('json', [place.owner], fields=ProfileForm._meta.fields)
        owner_data = json.loads(owner_data)[0]['fields']

        owner_form = ProfileForm(data=owner_data, instance=place.owner)
        place_form = PlaceForm(data=place_data, instance=place)

        data_correct = all([owner_form.is_valid(), place_form.is_valid()])  # We want both validations.
        viewresponse = {'result': data_correct}
        if not data_correct:
            viewresponse['err'] = OrderedDict()
            data_problems = set()
            for form in [owner_form, place_form]:
                viewresponse['err'].update({
                    str(form.fields[field_name].label) : list(field_errs)       # noqa: E203
                    for field_name, field_errs
                    in [(k, set(err for err in v if err)) for k, v in form.errors.items()]
                    if field_name != NON_FIELD_ERRORS and len(field_errs)
                })
                data_problems.update(form.errors.get(NON_FIELD_ERRORS, []))
            if len(data_problems):
                viewresponse['err'+NON_FIELD_ERRORS] = list(data_problems)
        else:
            place.set_check_status(self.request.user)

        if request.is_ajax():
            return JsonResponse(viewresponse)
        else:
            # Not implemented; only AJAX requests are expected.
            return TemplateResponse(request, self.template_name)


class PlaceListView(generic.ListView):
    model = Place


class PlaceStaffListView(AuthMixin, PlaceListView):
    """A place for supervisors to see an overview of and manage hosts in their area of responsibility."""
    template_name = "hosting/place_list_supervisor.html"
    minimum_role = SUPERVISOR

    def dispatch(self, request, *args, **kwargs):
        self.country = Country(kwargs['country_code'])
        kwargs['auth_base'] = self.country
        self.in_book = {'0': False, '1': True, None: None}[kwargs['in_book']]
        self.invalid_emails = kwargs['email']
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        return None

    def get_location(self, object):
        return object

    def get_queryset(self):
        self.base_qs = self.model.available_objects.filter(country=self.country.code)
        if self.in_book is not None:
            qs = self.base_qs.filter(in_book=self.in_book)
        else:
            qs = self.base_qs
        if self.invalid_emails:
            qs = qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX)
        return (qs.prefetch_related('owner__user', 'owner__phones')
                  .order_by('-confirmed', 'checked', 'owner__last_name'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_book_count'] = self.base_qs.filter(in_book=True).count()
        context['not_in_book_count'] = self.base_qs.filter(in_book=False).count()
        if self.in_book is not None:
            book_filter = models.Q(in_book=self.in_book)
            context['place_count'] = context['in_book_count'] if self.in_book else context['not_in_book_count']
        else:
            book_filter = models.Q()
            context['place_count'] = context['in_book_count'] + context['not_in_book_count']
        context['checked_count'] = self.base_qs.filter(book_filter, checked=True).count()
        context['confirmed_count'] = self.base_qs.filter(book_filter, confirmed=True).count()
        context['not_confirmed_count'] = context['place_count'] - context['confirmed_count']
        context['invalid_emails_count'] = self.base_qs.filter(
            owner__user__email__startswith=settings.INVALID_PREFIX).count()
        return context


class SearchView(PlaceListView):
    queryset = Place.objects.filter(available=True)
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        def unwhitespace(val):
            return " ".join(val.split())
        if 'ps_q' in request.GET:
            # Keeping Unicode in URL, replacing space with '+'.
            query = uri_to_iri(urlquote_plus(unwhitespace(request.GET['ps_q'])))
            params = {'query': query} if query else None
            return HttpResponseRedirect(reverse_lazy('search', kwargs=params))
        query = kwargs['query'] or ''  # Avoiding query=None
        self.query = unwhitespace(unquote_plus(query))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.result = geocode(self.query)
        if self.query and self.result.point:
            if any([self.result.state, self.result.city]):
                return (self.queryset
                            .annotate(distance=Distance('location', self.result.point))
                            .order_by('distance'))
            elif self.result.country:  # We assume it's a country
                return (self.queryset
                            .filter(country=self.result.country.upper())
                            .order_by('owner__user__last_login'))
        return self.queryset.order_by('owner__user__last_login')

    def get_detail_queryset(self):
        if len(self.query) <= 3:
            return self.queryset
        lookup = (
            Q(owner__user__username__icontains=self.query) |
            Q(owner__first_name__icontains=self.query) |
            Q(owner__last_name__icontains=self.query) |
            Q(closest_city__icontains=self.query)
        )
        return self.queryset.filter(lookup).select_related('owner__user')


class UserAuthorizeView(AuthMixin, generic.FormView):
    """Form view to add a user to the list of authorized users for a place to be able to see more details."""
    template_name = 'hosting/place_authorized_users.html'
    form_class = UserAuthorizeForm
    exact_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place, pk=self.kwargs['pk'])
        kwargs['auth_base'] = self.place
        return super().dispatch(request, *args, **kwargs)

    def get_permission_denied_message(self, object, context_omitted=False):
        return _("Only the owner of the place can access this page")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        m = re.match(r'^/([a-zA-Z]+)/', self.request.GET.get('next', default=''))
        if m:
            context['back_to'] = m.group(1).lower()

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
        return reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})

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


class FamilyMemberCreateView(
        CreateMixin, AuthMixin, FamilyMemberMixin,
        generic.CreateView):
    model = Profile
    form_class = FamilyMemberCreateForm

    def verify_anonymous_family(self):
        # Allow creation of only one completely anonymous family member.
        if self.place.family_is_anonymous:
            return HttpResponseRedirect(reverse_lazy(
                'family_member_update',
                kwargs={'pk': self.place.family_members_cache()[0].pk,
                        'place_pk': self.kwargs['place_pk']}
            ))
        else:
            return None

    def get(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs


class FamilyMemberUpdateView(
        UpdateMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin,
        generic.UpdateView):
    model = Profile
    form_class = FamilyMemberForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs


class FamilyMemberRemoveView(AuthMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place."""
    model = Profile
    template_name = 'hosting/family_member_confirm_delete.html'
    minimum_role = OWNER

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        return context


class FamilyMemberDeleteView(
        DeleteMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin,
        generic.DeleteView):
    """Remove the family member for the Place and delete it."""
    model = Profile

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.other_places.count() > 0:
            raise Http404("This family member is listed at other places as well; cannot delete the profile.")
        return self.object

    def delete(self, request, *args, **kwargs):
        redirect = super().delete(request, *args, **kwargs)
        self.place.family_members.remove(self.object)
        return redirect
