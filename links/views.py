from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired

from django.views import generic
from django.conf import settings


class UniqueLink(generic.TemplateView):
    template_name = 'links/links.html'

    def get(self, request, *args, **kwargs):
        self.token = kwargs.pop('token')
        s = URLSafeTimedSerializer(settings.SECRET_KEY, salt='salo')
        try:
            self.payload = s.loads(self.token, max_age=3)#600*24*60)
        except SignatureExpired:
            self.payload = 'SignatureExpired'
        except BadTimeSignature:
            self.payload = 'BadTimeSignature'
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['payload'] = self.payload
        return context

unique_link = UniqueLink.as_view()
