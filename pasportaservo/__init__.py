import postman


def patch_postman():
    from postman.utils import notify_user as original_notify_user

    def patched_notify_user(object, action, site):
        from postman.utils import notification
        from django.conf import settings
        if not notification:
            if action == 'rejection':
                user = object.sender
            elif action == 'acceptance':
                user = object.recipient
            else:
                user = None
            if user and user.email.startswith(settings.INVALID_PREFIX):
                return
        original_notify_user(object, action, site)

    postman.utils.notify_user = patched_notify_user


patch_postman()
