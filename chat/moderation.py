from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Max
from django.utils.translation import pgettext_lazy

from postman.models import (
    STATUS_ACCEPTED, STATUS_PENDING, STATUS_REJECTED, Message,
)

from hosting.models import Profile


def moderate_new_contact(message: Message) -> bool | None:
    if message.sender is None:
        return None   # Fall back to POSTMAN_AUTO_MODERATE_AS.
    if not message.sender.is_active or not message.sender.has_usable_password():
        return False  # Reject the contact attempt.

    reputation = {
        moderation_status: {'count': 0, 'latest': None}
        for moderation_status in (STATUS_ACCEPTED, STATUS_PENDING, STATUS_REJECTED)
    } | {
        row['moderation_status']: {k: v for k, v in row.items()}
        for row in (
            Message.objects
            .filter(sender=message.sender)
            .values('moderation_status')
            .annotate(count=Count('id'), latest=Max('sent_at'))
        )
    }

    if reputation[STATUS_ACCEPTED]['count'] == 0:
        message.moderation_reason = pgettext_lazy(
            "Chat moderation", "no earlier accepted messages")
        return None
    if reputation[STATUS_PENDING]['count'] > 0:
        message.moderation_reason = pgettext_lazy(
            "Chat moderation", "previous messages are still pending")
        return None
    if (
        reputation[STATUS_REJECTED]['count'] > 0
        and reputation[STATUS_REJECTED]['latest'] > reputation[STATUS_ACCEPTED]['latest']
    ):
        message.moderation_reason = pgettext_lazy(
            "Chat moderation", "previous message was rejected")
        return None

    try:
        message.sender._profile_examined = True  # type: ignore[attr-defined]
        details_change = (
            Profile.objects
            .filter(user=message.sender)
            .values_list('personal_details_changed_on', flat=True)
            .get()  # At this stage we do not need the full profile object for the user.
        )
        if details_change and details_change > reputation[STATUS_ACCEPTED]['latest']:
            message.moderation_reason = pgettext_lazy(
                "Chat moderation", "profile changed since last accepted message")
            return None
    except ObjectDoesNotExist:
        message.moderation_reason = pgettext_lazy(
            "Chat moderation", "sender has no profile set up")
        return None
    return True  # Allow the contact attempt.


def moderate_reply(message: Message) -> bool | None:
    if message.sender is None:
        return None  # Fall back to POSTMAN_AUTO_MODERATE_AS.
    return message.sender.is_active and message.sender.has_usable_password()
