from django import template
from django_countries.fields import Country
from ..models import Profile

register = template.Library()

@register.filter
def is_supervisor_of(user, profile_or_countries):
    try:
        user_profile = user.profile
    except (Profile.DoesNotExist, AttributeError):
        return False
    if isinstance(profile_or_countries, Country):
        return user_profile.is_supervisor_of(countries=[profile_or_countries])
    if isinstance(profile_or_countries, str):
        countries = profile_or_countries.split(' ')
        return user_profile.is_supervisor_of(countries=countries)
    if isinstance(profile_or_countries, Profile):
        return user_profile.is_supervisor_of(profile=profile_or_countries)
    if isinstance(profile_or_countries, int):
        profile = Profile.objects.get(pk=profile_or_countries)
        return user_profile.is_supervisor_of(profile=profile)
    return False
