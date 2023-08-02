from django.http import QueryDict
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest

from hosting.filters.search import SearchFilterSet
from hosting.forms.listing import SearchForm


@tag('forms', 'forms-search', 'search')
class SearchFormTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        # The search form is special in that it does not define any fields
        # itself but relies on them being injected via the SearchFilterSet.
        cls.SearchForm = SearchFilterSet().get_form_class()

    def test_init(self):
        self.assertTrue(issubclass(self.SearchForm, SearchForm))
        form = self.SearchForm()

        # Verify that the expected fields are part of the form.
        expected_fields = """
            max_guest max_night contact_before tour_guide have_a_drink
            owner__first_name owner__last_name available conditions
        """.split()
        self.assertEqual(set(expected_fields), set(form.fields))

        # Verify that no fields are marked 'required'.
        for field in expected_fields:
            with self.subTest(field=field):
                self.assertFalse(form.fields[field].required)

    @override_settings(LANGUAGE_CODE='en')
    def test_labels_en(self):
        # Workaround due to FilterSet evaluating labels too early.
        # https://github.com/carltongibson/django-filter/issues/1493
        Form = SearchFilterSet().get_form_class()
        form = Form()
        self.assertEqual(form.fields['max_guest'].label, "At least this many")
        self.assertEqual(
            form.fields['max_night'].label,
            "<span class=\"sr-only\">At least this many</span>")
        self.assertEqual(form.fields['contact_before'].label, "Available within")

        self.assertEqual(form.fields['available'].label, "Yes")
        self.assertTrue(hasattr(form.fields['available'], 'extra_label'))
        self.assertEqual(form.fields['available'].extra_label, "Place to sleep")
        self.assertEqual(form.fields['tour_guide'].label, "Yes")
        self.assertTrue(hasattr(form.fields['tour_guide'], 'extra_label'))
        self.assertEqual(form.fields['tour_guide'].extra_label, "Tour guide")
        self.assertEqual(form.fields['have_a_drink'].label, "Yes")
        self.assertTrue(hasattr(form.fields['have_a_drink'], 'extra_label'))
        self.assertEqual(form.fields['have_a_drink'].extra_label, "Have a drink")
        self.assertEqual(form.fields['conditions'].label, "Conditions")

        self.assertEqual(form.fields['owner__first_name'].label, "First name")
        self.assertEqual(form.fields['owner__last_name'].label, "Last name")

    @override_settings(LANGUAGE_CODE='eo')
    def test_labels_eo(self):
        # Workaround due to FilterSet evaluating labels too early.
        # https://github.com/carltongibson/django-filter/issues/1493
        Form = SearchFilterSet().get_form_class()
        form = Form()
        self.assertEqual(form.fields['max_guest'].label, "Almenaŭ tiom da")
        self.assertEqual(
            form.fields['max_night'].label,
            "<span class=\"sr-only\">Almenaŭ tiom da</span>")
        self.assertEqual(form.fields['contact_before'].label, "Disponebla ene de")

        self.assertEqual(form.fields['available'].label, "Jes")
        self.assertTrue(hasattr(form.fields['available'], 'extra_label'))
        self.assertEqual(form.fields['available'].extra_label, "Dormloko")
        self.assertEqual(form.fields['tour_guide'].label, "Jes")
        self.assertTrue(hasattr(form.fields['tour_guide'], 'extra_label'))
        self.assertEqual(form.fields['tour_guide'].extra_label, "Ĉiĉeronado")
        self.assertEqual(form.fields['have_a_drink'].label, "Jes")
        self.assertTrue(hasattr(form.fields['have_a_drink'], 'extra_label'))
        self.assertEqual(form.fields['have_a_drink'].extra_label, "Trinkejumado")
        self.assertEqual(form.fields['conditions'].label, "Kondiĉoj")

        self.assertEqual(form.fields['owner__first_name'].label, "Persona nomo")
        self.assertEqual(form.fields['owner__last_name'].label, "Familia nomo")

    def test_clean(self):
        # Checking the boolean fields on the form means
        # 'filter by these conditions' and is expected to
        # include them as True values in the form data.
        form = self.SearchForm(data=QueryDict(
            'max_guest=5&tour_guide=on&have_a_drink=on&available=on'
        ))
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        self.assertIn('max_guest', form.cleaned_data)
        self.assertEqual(form.cleaned_data['max_guest'], 5)
        self.assertIn('available', form.cleaned_data)
        self.assertEqual(form.cleaned_data['available'], True)
        self.assertIn('tour_guide', form.cleaned_data)
        self.assertEqual(form.cleaned_data['tour_guide'], True)
        self.assertIn('have_a_drink', form.cleaned_data)
        self.assertEqual(form.cleaned_data['have_a_drink'], True)

        # Unchecking the boolean fields on the form means
        # 'do not filter by these conditions' and is expected
        # to include them as None values in the form data.
        form = self.SearchForm(data=QueryDict('contact_before=5'))
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        self.assertIn('contact_before', form.cleaned_data)
        self.assertEqual(form.cleaned_data['contact_before'], 5)
        self.assertIn('available', form.cleaned_data)
        self.assertIsNone(form.cleaned_data['available'])
        self.assertIn('tour_guide', form.cleaned_data)
        self.assertIsNone(form.cleaned_data['tour_guide'])
        self.assertIn('have_a_drink', form.cleaned_data)
        self.assertIsNone(form.cleaned_data['have_a_drink'])

    def test_view_page(self):
        page = self.app.get(reverse('search'))
        self.assertEqual(page.status_code, 200)
        self.assertGreater(len(page.forms), 0)
        self.assertIn('filter', page.context)
        self.assertIsInstance(page.context['filter'].form, SearchForm)
