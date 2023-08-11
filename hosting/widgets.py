import re

from django.forms import widgets as form_widgets
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from crispy_forms.layout import Field as CrispyLayoutField
from crispy_forms.utils import TEMPLATE_PACK


class ClearableWithPreviewImageInput(form_widgets.ClearableFileInput):
    preview_template_name = 'ui/widget-image_file_preview.html'

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
    template_name = 'ui/widget-text+datalist.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['choices'] = self.choices
        context['widget']['attrs']['list'] = context['widget']['attrs']['id'] + '_options'
        return context


class CustomNullBooleanSelect(form_widgets.NullBooleanSelect):
    template_name = 'ui/widget-tristate_select.html'

    def __init__(self, label, choices, label_prefix=None, attrs=None):
        """
        @param `choices` must be an iterable of 2-tuples, where the 1st element of
        the tuple should be 'unknown', 'true', or 'false', with all three present.
        """
        super().__init__(attrs)
        self.choices = list(choices)
        self.label = label
        self.label_prefix = label_prefix

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['label'] = self.label
        context['widget']['label_prefix'] = self.label_prefix
        css_class = context['widget']['attrs'].get('class', '')
        if "form-control" not in css_class:
            context['widget']['attrs']['class'] = "form-control " + css_class
        context['widget']['attrs']['aria-labelledby'] = (
            context['widget']['attrs']['id'] + '_label'
        )
        return context


class MultiNullBooleanSelects(form_widgets.MultiWidget):
    def __init__(self, labels, choices_per_label, attrs=None):
        """
        @param `labels` is either an iterable or dict of 2-tuples, where the 1st
        element is the label of the enclosed widget and the 2nd element is the
        label's prefix (can be None). Dict keys are used as the name suffixes of
        the enclosed widgets.

        @param `choices_per_label` is an iterable  of 2-tuples, where the 1st
        element should be 'unknown', 'true', or 'false', with all three present.
        """
        if isinstance(labels, dict):
            widgets = {
                name: CustomNullBooleanSelect(label, choices_per_label, prefix)
                for name, (label, prefix) in labels.items()
            }
        else:
            widgets = [
                CustomNullBooleanSelect(label, choices_per_label, prefix)
                for label, prefix in labels
            ]
        super().__init__(widgets, attrs)

    def id_for_label(self, id_):
        return id_

    def decompress(self, value):
        # Typically used when value is not already a simple list of True-False-None.
        return [
            selected_value for id, selected_value in (
                value if isinstance(value, list)
                else map(lambda v: (None, v), re.split(r',\s*', str(value).strip()))
            )
        ]


class InlineRadios(CrispyLayoutField):
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


class ExpandedMultipleChoice(CrispyLayoutField):
    """
    Form Layout object that displays each option of a (Model)MultipleChoiceField
    as a separate label and a set of buttons corresponding to the choices of that
    option.
    """
    template = '%s/layout/expanded_select_field.html'

    def __init__(
            self, *args,
            option_css_classes=None, option_hover_css_classes=None,
            collapsed=None,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        if option_css_classes is not None:
            self.option_css_classes = option_css_classes
        else:
            self.option_css_classes = {}
        if option_hover_css_classes is not None:
            self.option_hover_css_classes = option_hover_css_classes
        else:
            self.option_hover_css_classes = {}
        self.collapsed_expanded_block = collapsed

    def render(self, *args, extra_context=None, **kwargs):
        if extra_context is None:
            extra_context = {}
        extra_context['option_css_classes'] = self.option_css_classes
        extra_context['option_hover_css_classes'] = self.option_hover_css_classes
        extra_context['field_block_collapsed'] = self.collapsed_expanded_block
        return super().render(*args, extra_context=extra_context, **kwargs)


class FormDivider:
    """
    Form Layout object for rendering a horizontal divider line on the form, with
    an optional title. The object cannot wrap other fields and should be used as
    a standalone element. It can optionally show a button for collapsing and
    un-collapsing a different form element, either given directly by its id or
    indirectly via the form field's name if the element corresponds to a field.
    """
    template_name = 'ui/widget-form_divider.html'

    def __init__(
            self, *,
            title=None, wrapper_class=None,
            collapse_field_name=None,
            collapse_field_id=None, collapse_field_label=None,
            collapsed=None,
            switch_button_class="btn-sm",
    ):
        self.divider_title = title
        self.wrapper_class = wrapper_class
        self.next_field = {
            'name': collapse_field_name,
            'id': collapse_field_id,
            'label': collapse_field_label,
            'collapsed': collapsed,
        }
        self.switch_button_class = switch_button_class

    def render(self, form, form_style, context, extra_context=None, **kwargs):
        if extra_context is None:
            extra_context = {}
        if self.next_field['name'] and not self.next_field['id']:
            self.next_field['id'] = form[self.next_field['name']].auto_id
            self.next_field['label'] = form[self.next_field['name']].label
        extra_context.update({
            'divider_title': self.divider_title,
            'wrapper_class': self.wrapper_class,
            'collapse_form_field_id': self.next_field['id'],
            'collapse_form_field_label': self.next_field['label'],
            'field_block_collapsed': self.next_field['collapsed'],
            'switch_button_class': self.switch_button_class,
        })
        template = get_template(self.template_name)
        with context.update(extra_context):
            return template.render(context.flatten())
