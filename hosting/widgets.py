from django.forms import widgets as form_widgets
from django.contrib.admin import widgets as admin_widgets
from django.utils.html import conditional_escape


class ClearableWithPreviewImageInput(form_widgets.ClearableFileInput):
    preview_template = (
        '<img %(id)s src="%(url)s" data-mfp-always height="42" style="margin: .1em 1em .1em .1em">'
        '<br class="visible-xxs-inline" />'
    )

    def render(self, name, value, attrs=None):
        self.field_name = name
        return super(ClearableWithPreviewImageInput, self).render(name, value, attrs)

    def get_template_substitution_values(self, value, **kwargs):
        substitute = super(ClearableWithPreviewImageInput, self).get_template_substitution_values(value)
        preview_id = 'id="%s-preview_id"' % self.field_name if hasattr(self, 'field_name')  \
                     else 'name="image-preview"'
        substitutions = {'url': conditional_escape(value.url), 'id': preview_id}
        substitutions.update(**kwargs)
        substitute['initial'] = self.preview_template % substitutions
        return substitute


class AdminImageWithPreviewWidget(ClearableWithPreviewImageInput, admin_widgets.AdminFileWidget):
    preview_template = (
        ClearableWithPreviewImageInput.preview_template +
        '<span style="margin-right: 1em">%(initial_raw_value)s</span>'
    )

    def get_template_substitution_values(self, value, **kwargs):
        substitutions = {'initial_raw_value': conditional_escape(value)}
        substitutions.update(**kwargs)
        return super(AdminImageWithPreviewWidget, self).get_template_substitution_values(value, **substitutions)

