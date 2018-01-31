from django.db.models import fields
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _


class StyledEmailField(fields.EmailField):
    @property
    def icon(self):
        template = ('<span class="fa fa-envelope" title="{title}" '
                    '      data-toggle="tooltip" data-placement="bottom"></span>')
        return format_html(template, title=_("email address").capitalize())
