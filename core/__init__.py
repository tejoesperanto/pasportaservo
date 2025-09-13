from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from hosting.models import PasportaServoUser


class PasportaServoHttpRequest(HttpRequest):
    user: 'PasportaServoUser'
    user_has_profile: bool

    skip_hosting_checks: bool
    DNT: bool

    is_json: bool
