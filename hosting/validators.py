from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .utils import split, title_with_particule


def validate_no_allcaps(value):
    """Tries to figure out wheather value is all caps and shouldn't.
    Validates until 3 characters and non latin strings.
    """
    if len(value) > 3 and value[-1:].isupper() and value == value.upper():
        correct_value = title_with_particule(value)
        message = _("Today is not CapsLock day. Please try with '{correct_value}'.")
        raise ValidationError(message.format(correct_value=correct_value))


def validate_not_to_much_caps(value):
    """Tries to figure out wheather value has too much caps.
    Maximum one capital per word.
    """
    nb_caps = sum(1 for c in value if c.isupper())
    words = split(value)
    nb_word = len(words)
    if not any(words):
        pass  # For non latin letters
    elif value == value.upper():
        pass  # Trusting validate_no_allcaps()
    elif nb_caps > nb_word:
        correct_value = title_with_particule(value)
        message = _("This seems there is too much uppercase letters. Try with '{correct_value}'.")
        raise ValidationError(message.format(correct_value=correct_value))
