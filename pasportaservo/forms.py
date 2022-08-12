from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist as ProfileDoesNotExist
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from postman.forms import (
    AnonymousWriteForm, FullReplyForm, QuickReplyForm, WriteForm,
)


class ChatMessageMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].label = _("Message")
        if 'recipients' in self.fields and hasattr(self.fields['recipients'], 'user_filter'):
            self.fields['recipients'].user_filter = self.user_filter

    def user_filter(self, recipient):
        try:
            if recipient.profile.death_date:
                if self.instance.sender:
                    raise ValidationError(
                        _("Cannot send the message: This user has passed away."),
                        code='deceased')
                else:
                    return ""  # Display the default sending rejection notification.
        except ProfileDoesNotExist:
            pass
        return None


class ChatMessageReplyMixin(object):
    def clean(self):
        """
        Check that messaging the recipient is still allowed.
        """
        if self.recipient and isinstance(self.recipient, get_user_model()):
            self.user_filter(self.recipient)
        return super().clean()


class CustomWriteForm(ChatMessageMixin, WriteForm):
    pass


class CustomAnonymousWriteForm(ChatMessageMixin, AnonymousWriteForm):
    pass


class CustomReplyForm(ChatMessageMixin, ChatMessageReplyMixin, FullReplyForm):
    pass


class CustomQuickReplyForm(ChatMessageMixin, ChatMessageReplyMixin, QuickReplyForm):
    pass
