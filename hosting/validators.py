from string import digits
from datetime import date
import re

from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils.text import format_lazy  # coming in Django 1.11
except ImportError:
    from django.utils.functional import keep_lazy_text
    format_lazy = keep_lazy_text(lambda s, *args, **kwargs: s.format(*args, **kwargs))

from .utils import split, title_with_particule


def validate_not_all_caps(value):
    """Tries to figure out whether the value is all caps while it shouldn't be.
    Validates until 3 characters and non latin strings.
    """
    if len(value) > 3 and value[-1:].isupper() and value == value.upper():
        message = _("Today is not CapsLock day. Please try with '{correct_value}'.")
        raise ValidationError(format_lazy(message, correct_value=title_with_particule(value)), code='caps')


def validate_not_too_many_caps(value):
    """Tries to figure out whether the value has too many capitals.
    Maximum two capitals per word.
    """
    authorized_begining = ("a", "de", "la", "mac", "mc")
    message = _("It seems there are too many uppercase letters. Please try with '{correct_value}'.")
    message = format_lazy(message, correct_value=title_with_particule(value))

    words = split(value)
    nb_word = len(words)
    if not any(words):
        pass  # For non latin letters
    elif value == value.upper():
        validate_not_all_caps(value)
    else:
        for word in words:
            nb_caps = sum(1 for char in word if char.isupper())
            if nb_caps > 1:
                if any([word.lower().startswith(s) for s in authorized_begining]):
                    # This should validate 'McCoy'
                    if nb_caps > 2:
                        raise ValidationError(message, code='caps')
                else:
                    raise ValidationError(message, code='caps')


def validate_no_digit(value):
    """Validates if there is not a digit in the string."""
    if any([char in digits for char in value]):
        raise ValidationError(validate_no_digit.message, code='digits')

validate_no_digit.constraint = ('pattern', '[^0-9]*')
validate_no_digit.message = _("Digits are not allowed.")


def validate_latin(value):
    """Validates if the string starts with latin characters."""
    if not re.match('^{}$'.format(validate_latin.constraint['pattern']), value):
        # http://kourge.net/projects/regexp-unicode-block
        raise ValidationError(validate_latin.message, code='non-latin')

validate_latin.constraint = {'pattern': r'[\u0041-\u005A\u0061-\u007A\u00C0-\u02AF\u0300-\u036F\u1E00-\u1EFF].*'}
validate_latin.message = _("Please provide this data in Latin characters, preferably in Esperanto. "
                           "The source language can be possibly stated in parentheses.")


def validate_not_in_future(datevalue):
    """Validates if the date is no later than today."""
    MaxValueValidator(date.today())(datevalue)


@deconstructible
class TooFarPastValidator(object):
    def __init__(self, number_years):
        self.number_years = number_years

    def __call__(self, datevalue):
        """Validates if the date is not earlier than the specified number of years ago."""
        now = date.today()
        try:
            back_in_time = now.replace(year=now.year - self.number_years)
        except ValueError:
            back_in_time = now.replace(year=now.year - self.number_years, day=now.day-1)
        MinValueValidator(back_in_time)(datevalue)

    def __eq__(self, other):
        return (isinstance(other, TooFarPastValidator) and self.number_years == other.number_years)

    def __ne__(self, other):
        return not (self == other)


@deconstructible
class TooNearPastValidator(TooFarPastValidator):
    def __call__(self, datevalue):
        """Validates if the date is not later than the specified number of years ago."""
        now = date.today()
        try:
            back_in_time = now.replace(year=now.year - self.number_years)
        except ValueError:
            back_in_time = now.replace(year=now.year - self.number_years, day=now.day-1)
        MaxValueValidator(back_in_time)(datevalue)


def validate_image(content):
    """Validate if Content Type is an image."""
    if getattr(content.file, 'content_type', None):
        content_type = content.file.content_type.split('/')[0]
        if content_type != 'image':
            raise ValidationError(_("File type is not supported"), code='file-type')


def validate_size(content):
    """Validate if the size of the content in not too big."""
    if content.file.size > validate_size.MAX_UPLOAD_SIZE:
        message = format_lazy(_("Please keep filesize under {limit}. Current filesize {current}"),
            limit=filesizeformat(validate_size.MAX_UPLOAD_SIZE),
            current=filesizeformat(content.file.size))
        raise ValidationError(message, code='file-size')

validate_size.MAX_UPLOAD_SIZE = 102400  # 100kB
validate_size.constraint = ('maxlength', validate_size.MAX_UPLOAD_SIZE)


def client_side_validated(form_class):
    original_init = form_class.__init__

    def _new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        for field in self._meta.model._meta.fields:
            if field.name not in self._meta.fields:
                continue
            for validator in field.validators:
                if hasattr(validator, 'constraint'):
                    constraint = getattr(validator, 'constraint', ())
                    if isinstance(constraint, dict):
                        try:
                            if len(constraint) != 1:
                                raise ImproperlyConfigured
                            constraint = dict(constraint).popitem()
                        except Exception as e:
                            pass
                    if len(constraint) != 2:
                        raise ImproperlyConfigured(
                            "Client-side constraint for '%s' validator on %s field "
                            "must consist of name and value only." % (
                            getattr(validator, '__name__', None) or getattr(type(validator), '__name__', None),
                            field
                        ))
                    self.fields[field.name].widget.attrs[constraint[0]] = constraint[1]
                    if hasattr(validator, 'message'):
                        msg_attr = 'data-error-{0}'.format(constraint[0])
                        self.fields[field.name].widget.attrs[msg_attr] = getattr(validator, 'message', "")

    form_class.__init__ = _new_init
    return form_class

