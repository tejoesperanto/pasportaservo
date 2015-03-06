import hashlib
import django.utils.http

def email_to_gravatar(email, fallback=''):
    mail_hash = hashlib.md5()
    mail_hash.update(email.encode('utf-8').lower().strip())
    
    if fallback != '':
        return "https://www.gravatar.com/avatar/{0}?d={1}".format(mail_hash.hexdigest(), django.utils.http.urlquote(fallback))
    else:
        return "https://www.gravatar.com/avatar/{0}".format(mail_hash.hexdigest())

