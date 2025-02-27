import hashlib
from urllib.parse import quote


def email_to_gravatar(email: str, fallback: str = '', size: int = 140):
    mail_hash = hashlib.sha256()
    mail_hash.update(email.encode('utf-8').lower().strip())

    if fallback:
        return "https://www.gravatar.com/avatar/{0}?d={1}&s={2}".format(
            mail_hash.hexdigest(),
            quote(fallback, safe=''),
            size or ''
        )
    else:
        return "https://www.gravatar.com/avatar/{0}".format(mail_hash.hexdigest())
