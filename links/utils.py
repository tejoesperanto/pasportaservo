from django.conf import settings
from django.urls import reverse

from itsdangerous import URLSafeTimedSerializer

from core.models import SiteConfiguration


def create_unique_url(payload, salt=None):
    config = SiteConfiguration.get_solo()
    salt = config.salt if salt is None else salt
    s = URLSafeTimedSerializer(settings.SECRET_KEY, salt=salt)
    token = s.dumps(payload)
    return reverse('unique_link', kwargs={'token': token}), token
