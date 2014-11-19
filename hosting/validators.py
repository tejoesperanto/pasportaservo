from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _

from .utils import split, title_with_particule


def validate_no_allcaps(value):
    """Tries to figure out whether value is all caps and shouldn't.
    Validates until 3 characters and non latin strings.
    """
    if len(value) > 3 and value[-1:].isupper() and value == value.upper():
        correct_value = title_with_particule(value)
        message = _("Today is not CapsLock day. Please try with '{correct_value}'.")
        raise ValidationError(message.format(correct_value=correct_value))


def validate_not_to_much_caps(value):
    """Tries to figure out whether value has too much caps.
    Maximum two capital per word.
    """
    authorized_begining = ('a', 'de', 'la', 'mac', 'mc')
    message = _("This seems there is too much uppercase letters. Try with '{correct_value}'.")
    message = message.format(correct_value=title_with_particule(value))

    words = split(value)
    nb_word = len(words)
    if not any(words):
        pass  # For non latin letters
    elif value == value.upper():
        validate_no_allcaps(value)
    else:
        for word in words:
            nb_caps = sum(1 for char in word if char.isupper())
            if nb_caps > 1:
                if any([word.lower().startswith(s) for s in authorized_begining]):
                    # This should validate 'McCoy'
                    if nb_caps > 2:
                        raise ValidationError(message)
                else:
                    raise ValidationError(message)


def validate_image(content):
    """Validate if Content Type is an image."""
    if getattr(content.file, 'content_type', None):
        content_type = content.file.content_type.split('/')[0]
        if content_type != 'image':
            raise ValidationError(_('File type is not supported'))


def validate_size(content):
    """Validate if the size of the content in not too big."""
    MAX_UPLOAD_SIZE = 102400  # 100kB
    if content.file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
            filesizeformat(MAX_UPLOAD_SIZE),
            filesizeformat(content.file.size))
        )
