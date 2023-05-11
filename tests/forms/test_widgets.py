import html
import json
import re

from django import forms
from django.contrib.gis.geos import Point as GeoPoint
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context
from django.test import TestCase, override_settings, tag

from factory import Faker

from hosting.widgets import (
    ClearableWithPreviewImageInput, CustomNullBooleanSelect,
    InlineRadios, MultiNullBooleanSelects, TextWithDatalistInput,
)
from maps.widgets import AdminMapboxGlWidget, MapboxGlWidget

from ..assertions import AdditionalAsserts


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

        result = widget.render(
            'null_bool_field', "X", attrs={'id': 'id_bool_field', 'class': "fancy"})
        self.assertRegex(
            result,
            r'<select [^>]*class="\s*(fancy\s*form-control|form-control\s*fancy)\s*"'
        )

        result = widget.render(
            'null_bool_field', "Y", attrs={'id': 'id_bool_field', 'class': "not-fancy"})
        self.assertRegex(
            result,
            r'<select [^>]*class="\s*(not-fancy\s*form-control|form-control\s*not-fancy)\s*"'
        )

        result = widget.render(
            'null_bool_field', "Z",
            attrs={'id': 'id_bool_field', 'class': "first-level form-control required"})
        self.assertRegex(
            result,
            r'<select [^>]*class="\s*(first-level form-control required)\s*"'
        )


@tag('forms', 'widgets')
class MultiNullBooleanSelectsWidgetTests(TestCase):
    def test_render_with_numbering(self):
        widget = MultiNullBooleanSelects(
            [("First", "Go"), ("Second", "Stop")],
            [('false', "kP"), ('unknown', "nM"), ('true', "hS")]
        )
        result = widget.render('multi_value_field', [], attrs={'id': 'id_multi_value_field'})
        self.assertRegex(
            result, '<span [^>]*id="id_multi_value_field_0_label">Go: First</span>')
        self.assertRegex(
            result, '<select\s+name="multi_value_field_0"\s+id="id_multi_value_field_0"')
        self.assertRegex(
            result, '<span [^>]*id="id_multi_value_field_1_label">Stop: Second</span>')
        self.assertRegex(
            result, '<select\s+name="multi_value_field_1"\s+id="id_multi_value_field_1"')

    def test_render_with_naming(self):
        widget = MultiNullBooleanSelects(
            {'go': ("First", None), 'stop': ("Second", None)},
            [('false', "kP"), ('unknown', "nM"), ('true', "hS")]
        )
        result = widget.render('multi_value_field', [], attrs={'id': 'id_multi_value_field'})
        self.assertRegex(
            result, '<span [^>]*id="id_multi_value_field_0_label">First</span>')
        self.assertRegex(
            result, '<select\s+name="multi_value_field_go"\s+id="id_multi_value_field_0"')
        self.assertRegex(
            result, '<span [^>]*id="id_multi_value_field_1_label">Second</span>')
        self.assertRegex(
            result, '<select\s+name="multi_value_field_stop"\s+id="id_multi_value_field_1"')


@tag('forms', 'widgets')
class InlineRadiosWidgetTests(TestCase):
    def test_render(self):
        class DummyForm(forms.Form):
            the_future = forms.ChoiceField(choices=[(5, "eV"), (6, "fU"), (7, "gT")])

        widget = InlineRadios('the_future')
        result = widget.render(DummyForm(), 'default', Context({}))
        result = ' '.join(result.split())  # Remove newlines and excessive whitespace.
        self.assertNotIn('<div class="radio">', result)
        self.assertRegex(
            result,
            '<label [^>]*for="id_the_future_1" [^>]*class="radio-inline *"'
        )

        widget = InlineRadios('the_future', radio_label_class="mark-me-up")
        result = widget.render(DummyForm(), 'default', Context({}))
        result = ' '.join(result.split())  # Remove newlines and excessive whitespace.
        self.assertNotIn('<div class="radio">', result)
        self.assertRegex(
            result,
            '<label [^>]*for="id_the_future_2" [^>]*class="radio-inline mark-me-up *"'
        )


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
        help_css_class = 'help' if self.widget_class is AdminMapboxGlWidget else 'help-block'
        with override_settings(LANGUAGE_CODE='en'):
            result = widget.render('location_field', None, attrs={'id': 'id_location_field'})
            result = ' '.join(result.split())
            # The template fragment is expected to include the container for the dynamic map.
            self.assertIn('<div id="map"></div>', result)
            # The template fragment is expected to include a fallback for no JavaScript.
            self.assertIn('<noscript>', result)
            # A note about technical requirements is expected.
            self.assertIn("The map requires JavaScript and the WebGL technology.", result)
            # A help text is expected.
            self.assertInHTML(
                f'<p class="{help_css_class}">'
                "Select manually the most suitable point on the map."
                '</p>',
                result)
            self.assertRegex(
                result,
                'id="id_location_field" [^>]*class="[^"]*monkey-patch[^"]*" [^>]*'
                'data-test-z="99" data-test-y="66" data-test-x="33"[^>]*?></'
            )
        with override_settings(LANGUAGE_CODE='eo'):
            result = widget.render(
                'location_field',
                GeoPoint(44.342639, -75.924861),
                attrs={'id': 'id_location_field'})
            result = ' '.join(result.split())
            # A translated note about technical requirements is expected.
            self.assertIn("La mapo necesigas JavaSkripton kaj la teĥnologion WebGL.", result)
            # A translated help text is expected.
            self.assertInHTML(
                f'<p class="{help_css_class}">'
                "Elektu permane la plej taŭgan punkton sur la mapo."
                '</p>',
                result)
            self.assertInHTML(
                html.escape(GeoPoint(44.342639, -75.924861).json),
                result)
            self.assertRegex(
                result,
                'id="id_location_field" .*?>[^<]+?coordinates'
            )

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
            self.assertRegex(result, 'id="id_position_field" [^>]*data-selectable-zoom="3"')
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
