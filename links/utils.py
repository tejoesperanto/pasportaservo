from itsdangerous import URLSafeTimedSerializer

from django.core.urlresolvers import reverse

from core.models import SiteConfiguration

config = SiteConfiguration.objects.get()


def create_unique_url(payload, salt=config.salt):
    s = URLSafeTimedSerializer(settings.SECRET_KEY, salt=salt)
    token = s.dumps(payload)
    return reverse('unique_link', kwargs={'token': token})
