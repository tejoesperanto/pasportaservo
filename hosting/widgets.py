from django.contrib.admin import widgets as admin_widgets
from django.forms import widgets as form_widgets
from django.template.loader import get_template
from django.utils.safestring import mark_safe


class ClearableWithPreviewImageInput(form_widgets.ClearableFileInput):
    preview_template_name = 'hosting/snippets/widget-image_file_preview.html'

    class ImagePreviewValue(object):
        def __init__(self, value, template):
            self.url = value.url
            self.template = template

        def __str__(self):
            return self.template

    def render(self, name, value, attrs=None, renderer=None):
        self.field_name = name
        return super().render(name, value, attrs, renderer)

    def format_value(self, value, **kwargs):
        if not self.is_initial(value):
            return
        preview_template = get_template(self.preview_template_name)
        substitutions = {'field_name': getattr(self, 'field_name', None), 'url': value.url}
        substitutions.update(**kwargs)
        rendered = mark_safe(preview_template.render(substitutions).strip())
        return self.ImagePreviewValue(value, rendered)


class AdminImageWithPreviewWidget(ClearableWithPreviewImageInput, admin_widgets.AdminFileWidget):
    preview_template_name = 'hosting/snippets/widget-image_file_preview_admin.html'

    def format_value(self, value, **kwargs):
        substitutions = {'initial_raw_value': value}
        substitutions.update(**kwargs)
        return super().format_value(value, **substitutions)


class TextWithDatalistInput(form_widgets.TextInput):
    template_name = 'hosting/snippets/widget-text+datalist.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['choices'] = self.choices
        context['widget']['attrs']['list'] = context['widget']['attrs']['id'] + '_options'
        return context
