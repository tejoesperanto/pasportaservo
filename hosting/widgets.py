from django.forms import widgets as form_widgets
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from crispy_forms.layout import Field as CrispyField
from crispy_forms.utils import TEMPLATE_PACK


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


class TextWithDatalistInput(form_widgets.TextInput):
    template_name = 'hosting/snippets/widget-text+datalist.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['choices'] = self.choices
        context['widget']['attrs']['list'] = context['widget']['attrs']['id'] + '_options'
        return context


class InlineRadios(CrispyField):
    """
    Form Layout object for rendering radio buttons inline.
    """
    template = '%s/layout/radioselect_inline.html'

    def __init__(self, *args, **kwargs):
        self.radio_label_class = kwargs.pop('radio_label_class', None)
        super().__init__(*args, **kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        extra_context = {'inline_class': 'inline'}
        if self.radio_label_class:
            extra_context['radio_label_class'] = self.radio_label_class
        return super().render(
            form, form_style, context, template_pack=template_pack,
            extra_context=extra_context
        )
