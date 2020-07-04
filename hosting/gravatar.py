import hashlib

import django.utils.http


def email_to_gravatar(email, fallback='', size=140):
    mail_hash = hashlib.md5()
    mail_hash.update(email.encode('utf-8').lower().strip())

    if fallback and fallback != '':
        return "https://www.gravatar.com/avatar/{0}?d={1}&s={2}".format(
            mail_hash.hexdigest(),
            django.utils.http.urlquote(fallback),
            size or ''
        )
    else:
        return "https://www.gravatar.com/avatar/{0}".format(mail_hash.hexdigest())
