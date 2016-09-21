
from itsdangerous import URLSafeTimedSerializer

def create_unique_url(self, payload, salt='salo'):
s = URLSafeTimedSerializer(settings.SECRET_KEY, salt=salt)
payload.update()
token = s.dumps(payload)
return reverse('unique_link', kwargs={'token': token})
