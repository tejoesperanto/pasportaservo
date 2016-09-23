from itsdangerous import URLSafeTimedSerializer

from django.conf import settings
from django.core.urlresolvers import reverse


def create_unique_url(payload, salt=settings.SALT):
    s = URLSafeTimedSerializer(settings.SECRET_KEY, salt=salt)
    token = s.dumps(payload)
    return reverse('unique_link', kwargs={'token': token})
