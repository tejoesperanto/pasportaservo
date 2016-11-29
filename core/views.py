from datetime import datetime

from markdown2 import markdown
from braces.views import AnonymousRequiredMixin, SuperuserRequiredMixin

from django.views import generic
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.template.loader import get_template
from django.template import Context
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from hosting.models import Place, Profile
from .forms import MassMailForm, UserRegistrationForm
from .utils import send_mass_html_mail

User = get_user_model()


class HomeView(generic.TemplateView):
    template_name = 'core/home.html'

home = HomeView.as_view()


class RegisterView(AnonymousRequiredMixin, generic.CreateView):
    model = User
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_create')

    def get_authenticated_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET['next']
        try:
            # When user is already authenticated, redirect to profile edit page.
            return self.request.user.profile.get_edit_url()
        except Profile.DoesNotExist:
            # If profile does not exist yet, redirect to profile creation page.
            return reverse_lazy('profile_create')

    def form_valid(self, form):
        self.object = form.save()
        # Keeping this on ice; it interferes with the inline login, probably by wiping the session vars.
        result = super(RegisterView, self).form_valid(form)
        # Log in user.
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'])
        login(self.request, user)
        messages.success(self.request, _("You are logged in."))
        return result

register = RegisterView.as_view()


class MassMailView(SuperuserRequiredMixin, generic.FormView):
    template_name = 'core/mass_mail_form.html'
    form_class = MassMailForm

    def get_success_url(self):
        return reverse_lazy('mass_mail_sent') + "?nb=" + str(self.nb_sent)

    def form_valid(self, form):
        body = form.cleaned_data['body']
        md_body = markdown(body)
        subject = form.cleaned_data['subject']
        preheader = form.cleaned_data['preheader']
        heading = form.cleaned_data['heading']
        category = form.cleaned_data['categories']
        default_from = settings.DEFAULT_FROM_EMAIL
        template = get_template('email/mass_email.html')

        opening = datetime(2014, 11, 24)
        places = Place.objects.select_related('owner__user')
        profiles = []

        if category in ("test", "just_user"):
            places = []
            # only active profiles, linked to existing user accounts
            profiles = Profile.objects.filter(user__isnull=False)
            # exclude completely those who have at least one active available place
            profiles = profiles.exclude(owned_places=Place.objects.filter(available=True))
            # remove profiles with places available in the past, that is deleted
            profiles = profiles.filter(Q(owned_places__available=False) | Q(owned_places__isnull=True))
            # finally remove duplicates
            profiles = profiles.distinct()
        elif category == "old_system":
            # those who logged in before the opening date; essentially, never used the new system
            profiles = Profile.objects.filter(user__last_login__lte=opening).distinct()
        else:
            # those who logged in after the opening date
            profiles = Profile.objects.filter(user__last_login__gt=opening)
            # filter by active places according to 'in-book?' selection
            if category == "in_book":
                profiles = profiles.filter(owned_places__in_book=True)
            elif category == "not_in_book":
                profiles = profiles.filter(owned_places__in_book=False, owned_places__available=True)
            # finally remove duplicates
            profiles = profiles.distinct()

        if category == 'test':
            test_email = form.cleaned_data['test_email']
            context = Context({
                'preheader': preheader,
                'heading': heading,
                'body': mark_safe(md_body.format(nomo=test_email)),
            })
            messages = [(
                subject,
                body.format(nomo=test_email),
                template.render(context),
                default_from,
                [test_email]
            )]

        else:
            context = Context({
                'preheader': preheader,
                'heading': heading,
                'body': mark_safe(md_body.format(nomo=profile.name)),
            })
            messages = [(
                subject,
                body.format(nomo=profile.name),
                template.render(context),
                default_from,
                [profile.user.email]
            ) for profile in profiles] if profiles else []

        self.nb_sent = send_mass_html_mail(messages)
        return super(MassMailView, self).form_valid(form)

mass_mail = MassMailView.as_view()


class MassMailSentView(SuperuserRequiredMixin, generic.TemplateView):
    template_name = 'hosting/mass_mail_sent.html'

    def get_context_data(self, **kwargs):
        context = super(MassMailSentView, self).get_context_data(**kwargs)
        context['nb'] = int(self.request.GET['nb']) if self.request.GET.get('nb', '').isdigit() else '??'
        return context

mass_mail_sent = MassMailSentView.as_view()
