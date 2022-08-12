import re
from datetime import date
from difflib import SequenceMatcher
from string import digits

from django.core.exceptions import (
    ImproperlyConfigured, ObjectDoesNotExist, ValidationError,
)
from django.core.validators import MaxValueValidator, MinValueValidator
from django.template.defaultfilters import filesizeformat
from django.utils.deconstruct import deconstructible
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from core.utils import getattr_, join_lazy, split

from .utils import title_with_particule, value_without_invalid_marker


def validate_not_all_caps(value):
    """
    Tries to figure out whether the value is all caps while it shouldn't be.
    Validates until 3 characters and non latin strings.
    """
    if len(value) > 3 and value[-1:].isupper() and value == value.upper():
        message = _("Today is not CapsLock day. Please try with '%(correct_value)s'.")
        raise ValidationError(message, code='caps', params={'correct_value': title_with_particule(value)})


def validate_not_too_many_caps(value):
    """
    Tries to figure out whether the value has too many capitals.
    Maximum two capitals per word.
    """
    authorized_beginning = ("a", "de", "la", "mac", "mc")
    message = _("It seems there are too many uppercase letters. Please try with '%(correct_value)s'.")
    correct_value = title_with_particule(value)

    words = split(value)
    if not any(words):
        pass  # For non-letters.
    elif value == value.upper():
        validate_not_all_caps(value)
    else:
        for word in words:
            nb_caps = sum(1 for char in word if char.isupper())
            if nb_caps > 1:
                if any([word.lower().startswith(s) for s in authorized_beginning]):
                    # This should validate 'McCoy'.
                    if nb_caps > 2:
                        raise ValidationError(message, code='caps', params={'correct_value': correct_value})
                else:
                    raise ValidationError(message, code='caps', params={'correct_value': correct_value})


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

validate_latin.constraint = {
    'pattern': r'[\u0041-\u005A\u0061-\u007A\u00C0-\u02AF\u0300-\u036F\u1E00-\u1EFF].*'}
validate_latin.message = _("Please provide this data in Latin characters, preferably in Esperanto. "
                           "The source language can be possibly stated in parentheses.")


def validate_not_in_future(datevalue):
    """Validates if the date is no later than today."""
    MaxValueValidator(date.today())(datevalue)


@deconstructible
class TooFarPastValidator():
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
        return (type(other) is self.__class__ and self.number_years == other.number_years)

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


@deconstructible
class AccountAttributesSimilarityValidator():
    def __init__(self, max_similarity=0.7):
        self.max_similarity = max(max_similarity, 0)

    def __eq__(self, other):
        return (type(other) is self.__class__ and self.max_similarity == other.max_similarity)

    def __ne__(self, other):
        return not (self == other)

    def __call__(self, value, user=None):
        """
        Validates that the given value is not too similar to known attributes of the account.
        """
        if not user:
            return

        account_attributes = [
            'username', 'email',
            'profile.first_name', 'profile.last_name', 'profile.email'
        ]
        similar_to_attributes = []
        value = value.lower()
        for attribute_path in account_attributes:
            try:
                path = attribute_path.split('.')
                attribute_name = path[-1]
                obj = getattr_(user, path[:-1])
                attribute = getattr(obj, attribute_name)
            except ObjectDoesNotExist:
                attribute = None
            if not attribute:
                continue
            if 'email' in attribute_name:
                attribute = value_without_invalid_marker(attribute)
            attribute = attribute.lower()

            for attribute_part in set(re.split(r'\W+', attribute) + [attribute, attribute[::-1]]):
                # The reverse value of the attribute is obtained quick-and-dirty, a more
                # complete approach is detailed in: https://stackoverflow.com/a/56282726.
                if self.exceeds_maximum_length_ratio(len(value), len(attribute_part)):
                    continue
                if (self.max_similarity == 0
                        or SequenceMatcher(a=value, b=attribute_part).quick_ratio() >= self.max_similarity):
                    verbose_name = obj._meta.get_field(attribute_name).verbose_name
                    similar_to_attributes.append(verbose_name)
                    break

        if similar_to_attributes:
            raise ValidationError(
                # Translators: This is a validation error already defined (and translated) by Django.
                _("The password is too similar to the %(verbose_name)s."),
                code='password_too_similar',
                params={'verbose_name': join_lazy(", ", similar_to_attributes)},
            )

    def exceeds_maximum_length_ratio(self, value_length, attribute_length):
        length_bound_similarity = self.max_similarity / 2 * value_length
        return attribute_length < length_bound_similarity and value_length >= 100 * attribute_length


def validate_image(content):
    """Validates if Content Type is an image."""
    try:
        content_type = content.file.content_type.split('/')[0]
    except (IOError, AttributeError):
        pass
    else:
        if content_type != 'image':
            raise ValidationError(_("File type is not supported."), code='file-type')


def validate_size(content):
    """Validates if the size of the content in not too big."""
    try:
        content_size = content.file.size
    except IOError:
        content_size = 0
    if content_size > validate_size.MAX_UPLOAD_SIZE:
        message = _("Please keep file size under %(limit)s. Current file size %(current_size)s.")
        raise ValidationError(message, code='file-size', params={
            'limit': lazy(filesizeformat, str)(validate_size.MAX_UPLOAD_SIZE),
            'current_size': lazy(filesizeformat, str)(content.file.size),
        })

validate_size.MAX_UPLOAD_SIZE = 102400  # 100kB
validate_size.constraint = ('maxlength', validate_size.MAX_UPLOAD_SIZE)


def client_side_validated(form_class):
    original_init = form_class.__init__

    def _new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        for field in self._meta.model._meta.get_fields():
            if field.name not in self._meta.fields:
                continue
            for validator in field.validators:
                if hasattr(validator, 'constraint'):
                    constraint = getattr(validator, 'constraint', ())
                    if isinstance(constraint, dict):
                        try:
                            if len(constraint) != 1:
                                constraint = []
                                raise ImproperlyConfigured
                            constraint = dict(constraint).popitem()
                        except Exception:
                            pass
                    if len(constraint) != 2:
                        raise ImproperlyConfigured(
                            "Client-side constraint for '{}' validator on {} field "
                            "must consist of name and value only.".format(
                                getattr(validator, '__name__', None) or getattr(type(validator), '__name__', None),
                                field
                            )
                        )
                    self.fields[field.name].widget.attrs[constraint[0]] = constraint[1]
                    if hasattr(validator, 'message'):
                        msg_attr = 'data-error-{0}'.format(constraint[0])
                        self.fields[field.name].widget.attrs[msg_attr] = getattr(validator, 'message', "")

    form_class.__init__ = _new_init
    return form_class
