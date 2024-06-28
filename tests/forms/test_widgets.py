import html
import json
import re

from django import forms
from django.contrib.gis.geos import Point as GeoPoint
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context
from django.test import TestCase, override_settings, tag

from bs4 import BeautifulSoup
from factory import Faker

from core.widgets import PasswordWithToggleInput
from hosting.widgets import (
    ClearableWithPreviewImageInput, CustomNullBooleanSelect,
    ExpandedMultipleChoice, FormDivider, InlineRadios,
    MultiNullBooleanSelects, TextWithDatalistInput,
)
from maps.widgets import AdminMapboxGlWidget, MapboxGlWidget

from ..assertions import AdditionalAsserts

HTML_PARSER = 'html.parser'


def safe_trim(value):
    return value.strip() if isinstance(value, str) else value


@tag('forms', 'widgets')
class PasswordWithToggleInputWidgetTests(AdditionalAsserts, TestCase):
    def test_render(self):
        widget_params = {
            'name': 'password_field',
            'value': "PA55w0rT",
            'attrs': {'id': 'id_password_field'},
        }

        widget = PasswordWithToggleInput(attrs={'autocomplete': 'current-password'})
        with override_settings(LANGUAGE_CODE='en'):
            result = widget.render(**widget_params)
        html = BeautifulSoup(result, HTML_PARSER)
        self.assertEqual(html.contents[0]['class'], ["input-group"])
        input_element = html.contents[0].input
        self.assertIsNotNone(input_element)
        self.assertNotIn('value', input_element.attrs)
        self.assertEqual(
            input_element.attrs,
            {
                'id': "id_password_field", 'name': "password_field",
                'type': "password", 'autocomplete': "current-password",
            }
        )
        button_element = html.find('button')
        self.assertIsNotNone(button_element)
        self.assertEqual(button_element.attrs.get('id'), "id_password_field_toggle")
        self.assertEqual(button_element.attrs.get('type'), "button")
        self.assertEqual(button_element.attrs.get('aria-pressed'), "false")
        self.assertEqual(''.join(button_element.stripped_strings), "Show")
        button_text_element = button_element.find_all('span', class_="password-toggle-text")
        self.assertLength(button_text_element, 1)
        self.assertEqual(button_text_element[0].attrs.get('data-label-inactive'), "Hide")
        self.assertCountEqual(
            button_element.parent.attrs['class'],
            ["password-toggle", "input-group-btn", "requires-scripting"]
        )

        widget = PasswordWithToggleInput(render_value=True)
        with override_settings(LANGUAGE_CODE='eo'):
            result = widget.render(**widget_params)
        html = BeautifulSoup(result, HTML_PARSER)
        input_element = html.contents[0].input
        self.assertIsNotNone(input_element)
        self.assertIn('value', input_element.attrs)
        self.assertEqual(input_element.attrs['value'], "PA55w0rT")
        button_element = html.find('button')
        self.assertIsNotNone(button_element)
        self.assertEqual(''.join(button_element.stripped_strings), "Montri")
        button_text_element = button_element.find_all('span', class_="password-toggle-text")
        self.assertLength(button_text_element, 1)
        self.assertEqual(button_text_element[0].attrs.get('data-label-inactive'), "Kaŝi")


@tag('forms', 'widgets')
class ClearableWithPreviewImageInputWidgetTests(TestCase):
    def test_format_value(self):
        widget = ClearableWithPreviewImageInput()
        self.assertIsNone(widget.format_value(None))
        self.assertIsNone(widget.format_value(""))
        self.assertIsNone(widget.format_value("test.jpeg"))

        faker = Faker._get_faker()
        dummy_file = SimpleUploadedFile(
            faker.file_name(category='image'), faker.image(size=(10, 10), image_format='png'))
        self.assertIsNone(widget.format_value(dummy_file))

        # We need to emulate django.db.models.fields.files.FieldFile without
        # actually creating one and its containing model.
        dummy_file.url = f"test_avatars/$/{dummy_file.name}.png"
        # A FieldFile-resembling value with a URL is expected to result in a
        # return value which can be converted to a template fragment.
        result = widget.format_value(dummy_file)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'url'))
        self.assertEqual(result.url, dummy_file.url)
        result_string = str(result)
        self.assertTrue(result_string.startswith('<img '))
        self.assertIn(f'src="{dummy_file.url}"', result_string)
        self.assertIn('name="image-preview"', result_string)

    def test_render(self):
        widget = ClearableWithPreviewImageInput()
        faker = Faker._get_faker()
        dummy_file = SimpleUploadedFile(
            faker.file_name(category='image'), faker.image(size=(10, 10), image_format='gif'))
        dummy_file.url = f"test_uploaded_pictures/$/{dummy_file.name}.gif"
        result = widget.render('picture_field', dummy_file, attrs={'id': 'id_picture_field'})
        result = ' '.join(result.split())  # Remove newlines and excessive whitespace.
        self.assertRegex(result, f'<img [^>]*src="{re.escape(dummy_file.url)}"')
        self.assertRegex(result, '<img [^>]*id="picture_field-preview_id"')


@tag('forms', 'widgets')
class TextWithDatalistInputWidgetTests(TestCase):
    def test_render(self):
        widget = TextWithDatalistInput()
        widget.choices = [(1, "Az"), (2, "By"), (3, "Cx"), (4, "Dw")]
        result = widget.render('code_field', None, attrs={'id': 'id_code_field'})
        result = ' '.join(result.split())  # Remove newlines and excessive whitespace.
        self.assertInHTML(
            '<input id="id_code_field" name="code_field" type="text" list="id_code_field_options">',
            result)
        self.assertRegex(result, '<datalist [^>]*id="id_code_field_options"')


@tag('forms', 'widgets')
class CustomNullBooleanSelectWidgetTests(TestCase):
    NULL_BOOLEAN_CHOICES = [('true', "hij"), ('false', "klm"), ('unknown', "nop")]

    def test_render(self):
        widget = CustomNullBooleanSelect("Pick one", self.NULL_BOOLEAN_CHOICES)

        result = widget.render('null_bool_field', None, attrs={'id': 'id_bool_field'})
        self.assertInHTML(
            '<span id="id_bool_field_label" class="control-label">Pick one</span>',
            result)
        self.assertInHTML(
            '''
            <select id="id_bool_field" name="null_bool_field"
                    aria-labelledby="id_bool_field_label" class="form-control">
                <option value="true">hij</option>
                <option value="false">klm</option>
                <option value="unknown" selected>nop</option>
            </select>
            ''',
            result)

        result = widget.render('null_bool_field', True, attrs={'id': 'id_bool_field'})
        self.assertInHTML('<option value="true" selected>hij</option>', result)
        self.assertInHTML('<option value="unknown">nop</option>', result)

        result = widget.render('null_bool_field', False, attrs={'id': 'id_bool_field'})
        self.assertInHTML('<option value="false" selected>klm</option>', result)
        self.assertInHTML('<option value="unknown">nop</option>', result)

    def test_render_with_prefix(self):
        widget = CustomNullBooleanSelect("Pick another", self.NULL_BOOLEAN_CHOICES, "Here")
        result = widget.render('null_bool_field', "?", attrs={'id': 'id_bool_field'})
        self.assertInHTML(
            '<span id="id_bool_field_label" class="control-label">Here: Pick another</span>',
            result)
        self.assertInHTML('<option value="unknown" selected>nop</option>', result)

    def test_css_class(self):
        widget = CustomNullBooleanSelect("Don't pick", self.NULL_BOOLEAN_CHOICES)

        test_data = [
            ("X", "fancy"),
            ("Y", "not-fancy"),
            ("Z", "first-level form-control required"),
        ]
        for value, css_classes in test_data:
            result = widget.render(
                'null_bool_field', value,
                attrs={'id': 'id_bool_field', 'class': css_classes})
            html = BeautifulSoup(result, HTML_PARSER)
            select_element = html.find('select')
            with self.subTest(css_class=css_classes, element=select_element):
                self.assertIsNotNone(select_element)
                for css_class in css_classes.split():
                    self.assertIn(css_class, select_element.attrs['class'])
                self.assertEqual(select_element.attrs['class'].count("form-control"), 1)


@tag('forms', 'widgets')
class MultiNullBooleanSelectsWidgetTests(TestCase):
    def test_render_with_numbering(self):
        widget = MultiNullBooleanSelects(
            [("First", "Go"), ("Second", "Stop")],
            [('false', "kP"), ('unknown', "nM"), ('true', "hS")]
        )
        result = widget.render('multi_value_field', [], attrs={'id': 'id_multi_value_field'})
        html = BeautifulSoup(result, HTML_PARSER)

        with self.subTest(container=' '.join(result.split())):
            with self.subTest(widget_qualifier=0):
                label_element = html.find('span', id='id_multi_value_field_0_label')
                self.assertIsNotNone(label_element)
                self.assertEqual(safe_trim(label_element.string), "Go: First")
                select_element = html.find(
                    'select', id='id_multi_value_field_0', attrs={'name': 'multi_value_field_0'})
                self.assertIsNotNone(select_element)

            with self.subTest(widget_qualifier=1):
                label_element = html.find('span', id='id_multi_value_field_1_label')
                self.assertIsNotNone(label_element)
                self.assertEqual(safe_trim(label_element.string), "Stop: Second")
                select_element = html.find(
                    'select', id='id_multi_value_field_1', attrs={'name': 'multi_value_field_1'})
                self.assertIsNotNone(select_element)

    def test_render_with_naming(self):
        widget = MultiNullBooleanSelects(
            {'go': ("First", None), 'stop': ("Second", None)},
            [('false', "kP"), ('unknown', "nM"), ('true', "hS")]
        )
        result = widget.render('multi_value_field', [], attrs={'id': 'id_multi_value_field'})
        html = BeautifulSoup(result, HTML_PARSER)

        with self.subTest(container=' '.join(result.split())):
            with self.subTest(widget_qualifier='go'):
                label_element = html.find('span', id='id_multi_value_field_0_label')
                self.assertIsNotNone(label_element)
                self.assertEqual(safe_trim(label_element.string), "First")
                select_element = html.find(
                    'select', id='id_multi_value_field_0', attrs={'name': 'multi_value_field_go'})
                self.assertIsNotNone(select_element)

            with self.subTest(widget_qualifier='stop'):
                label_element = html.find('span', id='id_multi_value_field_1_label')
                self.assertIsNotNone(label_element)
                self.assertEqual(safe_trim(label_element.string), "Second")
                select_element = html.find(
                    'select', id='id_multi_value_field_1', attrs={'name': 'multi_value_field_stop'})
                self.assertIsNotNone(select_element)


@tag('forms', 'widgets')
class InlineRadiosWidgetTests(TestCase):
    def test_render(self):
        class DummyForm(forms.Form):
            the_future = forms.ChoiceField(choices=[(5, "eV"), (6, "fU"), (7, "gT")])

        widget = InlineRadios('the_future')
        result = widget.render(DummyForm(), 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        with self.subTest(container=' '.join(result.split())):
            self.assertNotIn('<div class="radio">', result)
            label_element = html.find('label', attrs={'for': 'id_the_future_1'})
            self.assertIsNotNone(label_element)
            self.assertIn("radio-inline", label_element.attrs['class'])

        widget = InlineRadios('the_future', radio_label_class="mark-me-up")
        result = widget.render(DummyForm(), 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        with self.subTest(container=' '.join(result.split())):
            self.assertNotIn('<div class="radio">', result)
            label_element = html.find('label', attrs={'for': 'id_the_future_2'})
            self.assertIsNotNone(label_element)
            self.assertIn("radio-inline", label_element.attrs['class'])
            self.assertIn("mark-me-up", label_element.attrs['class'])


@tag('forms', 'widgets')
class ExpandedMultipleChoiceWidgetTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class MultiSelects(forms.widgets.MultiWidget):
            def decompress(self, value):
                return value or []

        class MultiChoicesField(forms.MultiValueField):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.widget = MultiSelects([f.widget for f in self.fields])

            def compress(self, data_list):
                return data_list

        class DummyForm(forms.Form):
            the_past = MultiChoicesField(
                [
                    forms.ChoiceField(choices=[
                        (101, "freshman"), (202, "sophomore"), (303, "junior"), (404, "senior"),
                    ]),
                    forms.ChoiceField(choices=[
                        (True, "diploma"), (False, "certificate"),
                    ]),
                ],
            )

        cls.DummyForm = DummyForm

    def test_render(self):
        widget = ExpandedMultipleChoice('the_past')

        form = self.DummyForm()
        result = widget.render(form, 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        # The form elements are expected to be rendered in a container corresponding
        # to the form's multi-value field.
        container_element = html.select('div#id_the_past_form_element')
        self.assertLength(container_element, 1)
        self.assertNotIn("collapse", container_element[0].attrs.get('class', {}))
        self.assertNotIn('aria-expanded', container_element[0].attrs)
        # No control label is expected to be rendered by default.
        self.assertLength(html.select('label.control-label'), 0)
        for i, subfield in enumerate(form.fields['the_past'].fields, start=1):
            element_id = f'id_the_past_option_{i}_form_element'
            with self.subTest(container_id=element_id):
                element = html.find('div', id=element_id, class_="form-group")
                self.assertIsNotNone(element)
                subelement = element.find('div', id=f'id_the_past_{i-1}')
                self.assertIsNotNone(subelement)
                self.assertIn("btn-group", subelement.attrs['class'])
                self.assertIn("btn-group-toggle", subelement.attrs['class'])
                for opt in subfield.choices:
                    optelement = subelement.find(
                        'input',
                        type='radio', attrs={'name': f'the_past_{i-1}', 'value': str(opt[0])})
                    with self.subTest(option=opt, element=optelement):
                        self.assertIsNotNone(optelement)
                        self.assertNotIn('checked', optelement.attrs)
                        # Each radio input field is expected to be wrapped by a label
                        # styled as a button with text corresponding to the option.
                        self.assertEqual(optelement.parent.name, 'label')
                        self.assertEqual(
                            optelement.attrs.get('id'), optelement.parent.attrs.get('for'))
                        self.assertIn("btn", optelement.parent.attrs['class'])
                        self.assertEqual(''.join(optelement.parent.stripped_strings), opt[1])
                        # Firefox's caching of radio input field values is expected
                        # to be disabled.
                        self.assertEqual(optelement.attrs.get('autocomplete'), 'off')
                        # A specific keyboard tabbing index for the multi-value field
                        # is not expected to be set.
                        self.assertNotIn('tabindex', optelement.attrs)

        form = self.DummyForm({'the_past_0': 303, 'the_past_1': True})
        result = widget.render(form, 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        for i, data in enumerate(form.data.items()):
            for opt in form.fields['the_past'].fields[i].choices:
                element = html.find(
                    'input', type='radio', attrs={'name': data[0], 'value': str(opt[0])})
                with self.subTest(option=opt, selected=opt[0] == data[1], element=element):
                    self.assertIsNotNone(element)
                    # Each radio input field is expected to be wrapped by a label
                    # styled as a button with text corresponding to the option.
                    self.assertEqual(element.parent.name, 'label')
                    self.assertIn("btn", element.parent.attrs['class'])
                    if opt[0] == data[1]:
                        # A value submitted as form data is expected to be selected.
                        self.assertIn('checked', element.attrs)
                        self.assertIn("active", element.parent.attrs['class'])
                    else:
                        # Any value not submitted as form data is expected to be not selected.
                        self.assertNotIn('checked', element.attrs)
                        self.assertNotIn("active", element.parent.attrs['class'])

    def test_css_classes(self):
        form = self.DummyForm()
        widget = ExpandedMultipleChoice(
            'the_past', wrapper_class="my-container", collapsed=False)
        result = widget.render(
            form, 'default',
            Context({'form_show_labels': True, 'tabindex': 3}),
        )
        html = BeautifulSoup(result, HTML_PARSER)
        # The form elements are expected to be rendered in a collapsible container
        # corresponding to the form's multi-value field and unfolded by default.
        container_element = html.find('div', id='id_the_past_form_element')
        self.assertIsNotNone(container_element)
        self.assertIn('class', container_element.attrs)
        self.assertIn("collapse", container_element.attrs['class'])
        self.assertIn("in", container_element.attrs['class'])
        self.assertEqual(container_element.attrs.get('aria-expanded'), 'true')
        for i, subfield in enumerate(form.fields['the_past'].fields, start=1):
            element_id = f'id_the_past_option_{i}_form_element'
            with self.subTest(container_id=element_id):
                # Each subfield of the form's multi-value field is expected to be
                # wrapped in a form-group with the specified wrapper CSS class.
                element = html.find('div', id=element_id, class_="form-group")
                self.assertIsNotNone(element)
                self.assertIn("my-container", element.attrs['class'])
                # The control label is expected to be present.
                label_element = element.label
                self.assertIsNotNone(label_element)
                self.assertEqual(label_element.attrs.get('for'), f'id_the_past_{i-1}')
                self.assertIn("control-label", label_element.attrs['class'])
                # When the subfield's CSS class is not specified, only the default
                # classes are expected to be in use.
                subelement = element.find('div', id=f'id_the_past_{i-1}')
                self.assertIsNotNone(subelement)
                self.assertCountEqual(
                    subelement.parent.attrs['class'],
                    ["controls", "checkbox"])
                for opt in subfield.choices:
                    optelement = subelement.find(
                        'input',
                        type='radio', attrs={'name': f'the_past_{i-1}', 'value': str(opt[0])})
                    with self.subTest(option=opt, element=optelement):
                        self.assertIsNotNone(optelement)
                        # The specified keyboard tabbing index for the multi-value
                        # field is expected to be set.
                        self.assertEqual(optelement.attrs.get('tabindex'), '3')
                        # The label wrapping each radio input field is expected to
                        # have no hover CSS class.
                        self.assertEqual(optelement.parent.name, 'label')
                        self.assertEqual(
                            optelement.parent.attrs.get('data-hover-class', ""), "")

        widget = ExpandedMultipleChoice(
            'the_past',
            option_css_classes={202: "current-class"},
            option_hover_css_classes={False: "btn-lg", True: "btn-lg"},
            collapsed=True)
        result = widget.render(
            form, 'default',
            Context({
                'form_show_labels': True,
                'label_class': "custom-label",
                'field_class': "custom-controls",
            }),
        )
        html = BeautifulSoup(result, HTML_PARSER)
        # The form elements are expected to be rendered in a collapsible container
        # corresponding to the form's multi-value field and folded by default.
        container_element = html.find('div', id='id_the_past_form_element')
        self.assertIsNotNone(container_element)
        self.assertIn('class', container_element.attrs)
        self.assertIn("collapse", container_element.attrs['class'])
        self.assertNotIn("in", container_element.attrs['class'])
        self.assertEqual(container_element.attrs.get('aria-expanded'), 'false')
        # The control labels are expected to be rendered with the specified CSS class.
        label_elements = html.select('label.control-label')
        self.assertLength(label_elements, 2)
        for label_element in label_elements:
            self.assertIn("custom-label", label_element.attrs['class'])
        for i, subfield in enumerate(form.fields['the_past'].fields, start=1):
            # The specified subfield's CSS class is expected to be used.
            subelement = html.find('div', id=f'id_the_past_{i-1}')
            self.assertIsNotNone(subelement)
            self.assertCountEqual(
                subelement.parent.attrs['class'],
                ["custom-controls", "controls", "checkbox"])
            for opt in subfield.choices:
                option_element = subelement.find(
                    'input',
                    type='radio', attrs={'name': f'the_past_{i-1}', 'value': str(opt[0])})
                with self.subTest(option=opt, element=option_element):
                    self.assertIsNotNone(option_element)
                    # The labels wrapping the radio input fields are expected to have
                    # the specified CSS class(es), corresponding to the options, and
                    # the hover CSS class specified per each option.
                    label_element = option_element.parent
                    self.assertEqual(label_element.name, 'label')
                    if opt[0] in [202]:
                        presence_assertion = self.assertIn
                    else:
                        presence_assertion = self.assertNotIn
                    presence_assertion("current-class", label_element.attrs['class'])
                    self.assertNotIn("custom-label", label_element.attrs['class'])
                    self.assertEqual(
                        label_element.attrs.get('data-hover-class', ""),
                        "btn-lg" if opt[0] in [True, False] else ""
                    )

        widget = ExpandedMultipleChoice('the_past')
        context = Context({'label_class': "custom-label"})
        result = widget.render(
            form, 'default', context,
            extra_context={'inline_class': "select-inline"},
        )
        html = BeautifulSoup(result, HTML_PARSER)
        # No control label is expected to be rendered by default.
        self.assertLength(html.select('label.control-label'), 0)
        self.assertLength(html.select('label.custom-label'), 0)
        # Unknown values in extra rendering context are not supposed to be used.
        self.assertNotIn('inline_class', context)
        self.assertNotIn('inline_class', result)
        self.assertNotIn("select-inline", result)


@tag('forms', 'widgets')
class FormDividerWidgetTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class DummyForm(forms.Form):
            all_years = forms.IntegerField(label="All Years")

        cls.DummyForm = DummyForm

    def test_render(self):
        widget = FormDivider()
        result = widget.render(self.DummyForm(), 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        # The widget is expected to be composed of a container (with no ID)
        # and a single element for the horizontal divider.
        element = html.select('.form-divider')
        self.assertLength(element, 1)
        element = element[0]
        self.assertNotIn('id', element.attrs)
        self.assertEqual(element.attrs['class'], ["form-divider"])
        subelement = element.select('.divider-heading')
        self.assertLength(subelement, 1)
        subelement = subelement[0]
        self.assertLength(subelement.attrs['class'], 1)
        # The sub-element is expected to have no content and no ARIA role.
        self.assertNotIn('aria-role', subelement.attrs)
        self.assertEqual(subelement.contents, [])
        self.assertIsNone(element.find('button'))
        # A specific keyboard tabbing index for the divider form element
        # is not expected to be set.
        self.assertNotIn('tabindex', result)

        widget = FormDivider(title="monkeying Around")
        for show_labels in (False, True):
            with self.subTest(show_labels=show_labels):
                context = Context({'form_show_labels': show_labels, 'tabindex': 3})
                result = widget.render(
                    self.DummyForm(), 'default', context,
                    extra_context={'inline_label': "monkeyshines"})
                html = BeautifulSoup(result, HTML_PARSER)
                element = html.find(None, "form-divider")
                self.assertIsNotNone(element)
                subelement = element.find(None, "divider-heading", recursive=False)
                self.assertIsNotNone(subelement)
                if not show_labels:
                    # When form labels are turned off, no text is expected to be
                    # rendered on the horizontal divider sub-element, even if provided.
                    # The sub-element is expected to have no ARIA role, as it is purely
                    # decorative.
                    self.assertLength(subelement.attrs['class'], 1)
                    self.assertNotIn('aria-role', subelement.attrs)
                    self.assertEqual(subelement.contents, [])
                else:
                    # When form labels are turned on, the given title is expected to be
                    # rendered on the horizontal divider sub-element, and the
                    # sub-element is expected to have the suitable ARIA role.
                    self.assertIn("has-content", subelement.attrs['class'])
                    self.assertEqual(subelement.attrs.get('aria-role'), 'separator')
                    self.assertEqual(subelement.string, "monkeying Around")
                # A specific keyboard tabbing index for the divider form element is not
                # expected to be set (the element is expected to be unreachable by the
                # keyboard).
                self.assertNotIn('tabindex', result)
                # Unknown values in extra rendering context are not supposed to be used.
                self.assertNotIn('inline_label', context)
                self.assertNotIn('inline_label', result)
                self.assertNotIn("monkeyshines", result)

    def test_css_class(self):
        widget = FormDivider(wrapper_class="my-container")
        result = widget.render(self.DummyForm(), 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        element = html.select('.my-container')
        self.assertLength(element, 1)
        # The given wrapping class is expected for the container element.
        self.assertCountEqual(element[0].attrs['class'], ["form-divider", "my-container"])

    def switch_rendering_tests(
            self, render_output, lang,
            *, expected_field_id, expected_label, collapsed, tabindex=None,
    ):
        html = BeautifulSoup(render_output, HTML_PARSER)

        # The widget which has a collapsing control enabled is expected
        # to be composed of a container inside of which a switch button
        # controlling the folding of the other form element and an
        # element for the horizontal divider.
        element = html.find(None, "form-divider")
        self.assertIsNotNone(element)
        switch_element = element.find('button', recursive=False)
        self.assertIsNotNone(switch_element)
        self.assertEqual(switch_element.attrs.get('id'), f'{expected_field_id}_switch')
        # The switch button is expected to have the default CSS classes.
        self.assertIn("switch", switch_element.attrs['class'])
        self.assertIn("btn", switch_element.attrs['class'])
        self.assertIn("btn-sm", switch_element.attrs['class'])
        if tabindex is None:
            # When no explicit keyboard tabbing index is specified, it is
            # expected to not be set for the switch button.
            self.assertNotIn('tabindex', switch_element.attrs)
        else:
            # When a keyboard tabbing index is specified, it is expected
            # to be set for the switch button.
            self.assertIn('tabindex', switch_element.attrs)
            self.assertEqual(switch_element.attrs['tabindex'], str(tabindex))
        # The switch button is expected to control the given form element.
        self.assertEqual(
            switch_element.attrs.get('aria-controls'),
            f'{expected_field_id}_form_element'
        )

        switch_icon_element = switch_element.find(None, "fa", recursive=False)
        self.assertIsNotNone(switch_icon_element)
        # The switch button is expected to indicate the ARIA 'expanded'
        # state of the other form element according to the initial mode.
        self.assertEqual(
            switch_element.attrs.get('aria-expanded'),
            'false' if collapsed else 'true'
        )
        self.assertIn("fa-caret-right", switch_icon_element.attrs['class'])
        if not collapsed:
            # A visual indicator of the 'expanded' state is expected on
            # the switch button.
            self.assertIn("fa-rotate-90", switch_icon_element.attrs['class'])

        # The switch button is expected to have a suitable ARIA label.
        label_show = {
            'en': f"{expected_label}: Show" if expected_label else "Show",
            'eo': f"{expected_label}: Montri" if expected_label else "Montri",
        }
        label_hide = {
            'en': f"{expected_label}: Hide" if expected_label else "Hide",
            'eo': f"{expected_label}: Kaŝi" if expected_label else "Kaŝi",
        }
        self.assertEqual(
            safe_trim(switch_icon_element.attrs.get('aria-label')),
            label_show[lang].strip() if collapsed else label_hide[lang].strip()
        )
        self.assertEqual(
            safe_trim(switch_icon_element.attrs.get('data-aria-label-inactive')),
            label_hide[lang].strip() if collapsed else label_show[lang].strip()
        )

        # The switch button is expected to be followed by the horizontal
        # divider element.
        divider_element = switch_element.find_next_sibling(None, "divider-heading")
        self.assertIsNotNone(divider_element)

    def test_render_switch_for_field_name(self):
        # When the collapsible form element is indicated by the corresponding
        # form field's name, which is not among the form's fields, a KeyError
        # exception is expected and no widget rendered.
        with self.assertRaises(KeyError):
            widget = FormDivider(collapse_field_name='first_year')
            widget.render(self.DummyForm(), 'default', Context({}))

        for initially_collapsed in (None, False, True):
            with self.subTest(collapsed=initially_collapsed):
                with self.assertNotRaises(KeyError):
                    widget = FormDivider(
                        title="monKey",
                        collapse_field_name='all_years', collapse_field_label="Lui",
                        collapsed=initially_collapsed)
                    for lang in ['en', 'eo']:
                        with self.subTest(lang=lang):
                            with override_settings(LANGUAGE_CODE=lang):
                                result = widget.render(
                                    self.DummyForm(), 'default', Context({}))
                            # The switch button is expected to control the form element
                            # identified by the ID of the given form field and the
                            # actual form field's label is expected to override the
                            # custom label given to the widget.
                            self.switch_rendering_tests(
                                result, lang, collapsed=initially_collapsed,
                                expected_field_id='id_all_years', expected_label="All Years")

    def test_render_switch_for_field_id(self):
        for initially_collapsed in (None, False, True):
            with self.subTest(collapsed=initially_collapsed):
                # Explicit form field ID is expected to take preference over the field
                # name, if both are given.
                with self.assertNotRaises(KeyError):
                    widget = FormDivider(
                        collapse_field_name='future_years',
                        collapse_field_id='id_other_years', collapse_field_label="Lui",
                        collapsed=initially_collapsed)
                    for lang in ['en', 'eo']:
                        with self.subTest(lang=lang):
                            with override_settings(LANGUAGE_CODE=lang):
                                result = widget.render(
                                    self.DummyForm(), 'default', Context({}))
                            # The switch button is expected to control the form element
                            # identified by the given ID (even if a form field name is
                            # also given) and the given custom label is expected to be
                            # used in all cases.
                            self.switch_rendering_tests(
                                result, lang, collapsed=initially_collapsed,
                                expected_field_id='id_other_years', expected_label="Lui")

        # If a custom field label is given (alongside a specific element
        # ID) it is expected to be used on the switch button; otherwise,
        # if a title is given, it is expected to be used. If none of these
        # two are given, the ARIA label of the switch button is expected
        # to be the default one corresponding to the element's 'expanded'
        # state.
        for title in ("monKey", " ", None):
            for custom_label in ("Lui", " ", None):
                with self.subTest(
                        has_title=title is not None,
                        field_has_label=custom_label is not None,
                ):
                    widget = FormDivider(
                        title=title,
                        collapse_field_name='all_years',
                        collapse_field_id='id_other_years', collapse_field_label=custom_label,
                    )
                    for lang in ['en', 'eo']:
                        with self.subTest(lang=lang):
                            with override_settings(LANGUAGE_CODE=lang):
                                result = widget.render(
                                    self.DummyForm(), 'default', Context({'tabindex': 5}))
                            # The switch button is expected to control the form element
                            # identified by the given ID and to be reachable via the
                            # given keyboard tabbing index.
                            self.switch_rendering_tests(
                                result, lang, collapsed=None, tabindex=5,
                                expected_field_id='id_other_years',
                                expected_label=custom_label or title or None)

    def test_switch_css_class(self):
        widget = FormDivider(switch_button_class="danger btn-lg", collapse_field_id='id_test')
        result = widget.render(self.DummyForm(), 'default', Context({}))
        html = BeautifulSoup(result, HTML_PARSER)
        element = html.find(None, "form-divider")
        self.assertIsNotNone(element)
        switch_element = element.find('button', recursive=False)
        self.assertIsNotNone(switch_element)
        self.assertIn("switch", switch_element.attrs['class'])
        # The given CSS classes are expected for the switch button.
        self.assertIn("btn-lg", switch_element.attrs['class'])
        self.assertIn("danger", switch_element.attrs['class'])
        # The default CSS class is expected to be not present on the button.
        self.assertNotIn("btn-sm", switch_element.attrs['class'])


@tag('forms', 'widgets')
class MapboxGlWidgetTests(AdditionalAsserts, TestCase):
    widget_class = MapboxGlWidget

    def test_media(self):
        widget = self.widget_class()
        css_media = str(widget.media['css'])
        self.assertRegex(css_media, r'href=".*?/mapbox-gl\.css"')
        js_media = str(widget.media['js'])
        self.assertRegex(js_media, r'src=".*?/mapbox-gl\.js"')
        self.assertRegex(js_media, r'src=".*?/mapbox-gl-widget\.js"')
        self.assertRegex(js_media, r'src=".*?/endpoints/\?format=js\&amp;type=widget"')

    def test_serialize(self):
        widget = self.widget_class()
        self.assertEqual(widget.serialize(None), '')
        self.assertEqual(widget.serialize(""), '')
        self.assertEqual(widget.serialize(GeoPoint()), '')

        result = widget.serialize(GeoPoint(44.342639, -75.924861))
        self.assertSurrounding(result, '{', '}')
        self.assertEqual(
            json.loads(result),
            {'coordinates': [44.342639, -75.924861], 'type': 'Point'}
        )

    def test_render(self):
        widget = self.widget_class(
            {'class': "monkey-patch", 'data-test-z': 99, 'data-test-y': 66, 'data-test-x': 33})
        help_css_class = "help" if self.widget_class is AdminMapboxGlWidget else "help-block"
        with override_settings(LANGUAGE_CODE='en'):
            result = widget.render('location_field', None, attrs={'id': 'id_location_field'})
            dom_tree = BeautifulSoup(result, HTML_PARSER)
            # The template fragment is expected to include the container for the dynamic map.
            map_container_element = dom_tree.find('div', id='map')
            self.assertIsNotNone(map_container_element)
            self.assertLength(map_container_element.contents, 0)
            # The template fragment is expected to include a fallback for no JavaScript.
            noscript_element = dom_tree.find('noscript')
            self.assertIsNotNone(noscript_element)
            # A note about technical requirements is expected.
            self.assertIn(
                "The map requires JavaScript and the WebGL technology.",
                noscript_element.stripped_strings)
            # A help text is expected.
            help_element = dom_tree.find('p', help_css_class)
            self.assertIsNotNone(help_element)
            self.assertEqual(
                safe_trim(help_element.string),
                "Select manually the most suitable point on the map.")
            # The location field is expected to include the specified attributes.
            field_element = dom_tree.find(id='id_location_field')
            self.assertIsNotNone(field_element)
            self.assertIn("monkey-patch", field_element.attrs['class'])
            self.assertEqual(field_element.attrs.get('data-test-x'), '33')
            self.assertEqual(field_element.attrs.get('data-test-y'), '66')
            self.assertEqual(field_element.attrs.get('data-test-z'), '99')
        with override_settings(LANGUAGE_CODE='eo'):
            result = widget.render(
                'location_field',
                GeoPoint(44.342639, -75.924861),
                attrs={'id': 'id_location_field'})
            dom_tree = BeautifulSoup(result, HTML_PARSER)
            # A translated note about technical requirements is expected.
            noscript_element = dom_tree.find('noscript')
            self.assertIsNotNone(noscript_element)
            self.assertIn(
                "La mapo necesigas JavaSkripton kaj la teĥnologion WebGL.",
                noscript_element.stripped_strings)
            # A translated help text is expected.
            help_element = dom_tree.find('p', help_css_class)
            self.assertIsNotNone(help_element)
            self.assertEqual(
                safe_trim(help_element.string),
                "Elektu permane la plej taŭgan punkton sur la mapo.")
            # The location field is expected to include the specified GeoPoint.
            self.assertInHTML(
                html.escape(GeoPoint(44.342639, -75.924861).json),
                result)
            field_element = dom_tree.find(id='id_location_field')
            self.assertIsNotNone(field_element)
            self.assertRegex(field_element.string, r'\Wcoordinates\W')

    def test_selectable_zoom(self):
        widget = self.widget_class({'data-selectable-zoom': 3})
        with override_settings(LANGUAGE_CODE='en'):
            result = widget.render('position_field', None, attrs={'id': 'id_position_field'})
            result = ' '.join(result.split())
            # The template fragment is expected to include a note about map scale.
            self.assertIn(
                "It will be possible to register the point when the resolution of the map allows "
                "for visible distances of about 1km or less.",
                result)
            dom_tree = BeautifulSoup(result, HTML_PARSER)
            field_element = dom_tree.find(id='id_position_field')
            self.assertIsNotNone(field_element)
            self.assertEqual(field_element.attrs.get('data-selectable-zoom'), '3')
        with override_settings(LANGUAGE_CODE='eo'):
            result = widget.render('position_field', None, attrs={'id': 'id_position_field'})
            result = ' '.join(result.split())
            # The template fragment is expected to include a translated note about map scale.
            self.assertIn(
                "Eblus registri la punkton kiam la distingivo de la mapo permesus distingeblajn "
                "distancojn de ĉirkaŭ 1km aŭ malpli.",
                result)


@tag('admin')
class AdminMapboxGlWidgetTests(MapboxGlWidgetTests):
    widget_class = AdminMapboxGlWidget
