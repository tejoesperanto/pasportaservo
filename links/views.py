from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views import generic

from itsdangerous import (
    BadSignature, BadTimeSignature, SignatureExpired, URLSafeTimedSerializer,
)

from core.models import SiteConfiguration
from core.views import EmailUpdateConfirmView
from hosting.models import Place


class UniqueLinkView(generic.TemplateView):
    def get(self, request, *args, **kwargs):
        config = SiteConfiguration.get_solo()
        self.token = kwargs.pop('token')
        s = URLSafeTimedSerializer(settings.SECRET_KEY, salt=config.salt)
        try:
            payload = s.loads(self.token, max_age=config.token_max_age)
        except SignatureExpired:
            self.template_name = 'links/signature_expired.html'
        except BadTimeSignature:
            self.template_name = 'links/bad_time_signature.html'
        except BadSignature:
            self.template_name = 'links/invalid_link.html'
        else:
            return self.redirect(request, payload, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def redirect(self, request, payload, *args, **kwargs):
        try:
            action = payload['action']
        except KeyError:
            self.template_name = 'links/invalid_link.html'
            return super().get(request, *args, **kwargs)
        return getattr(self, 'redirect_' + action)(request, payload)

    def redirect_confirm(self, request, payload):
        place = get_object_or_404(Place, pk=payload['place'])
        if place.confirmed and place.owner.confirmed:
            return HttpResponseRedirect(reverse('info_already_confirmed'))
        place.owner.confirm_all_info()
        url = reverse('profile_edit', kwargs={'pk': place.owner.pk})
        msg = _("Good, your data are confirmed. Look at <a href=\"{url}\">your profile</a>!")
        messages.info(request, format_html(msg, url=url))
        return HttpResponseRedirect(reverse('info_confirmed'))

    def redirect_update(self, request, payload):
        place = get_object_or_404(Place, pk=payload['place'])
        place.owner.user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, place.owner.user)
        messages.info(request, _("You've been automatically logged in. Happy editing!"))
        return HttpResponseRedirect(place.owner.get_absolute_url())

    def redirect_email_update(self, request, payload):
        email_update_confirm = EmailUpdateConfirmView.as_view()
        return email_update_confirm(request, pk=payload['pk'], email=payload['email'],
                                    verification=payload['v'] if 'v' in payload else False)


class ConfirmedView(generic.TemplateView):
    template_name = 'links/confirmed.html'


class AlreadyConfirmedView(generic.TemplateView):
    template_name = 'links/already_confirmed.html'
