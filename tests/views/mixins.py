from django.test import override_settings

from .. import with_type_hint
from .pages.base import PageWithFormTemplate
from .testcasebase import BasicViewTests


class FormViewTestsMixin(with_type_hint(BasicViewTests)):
    view_page: type[PageWithFormTemplate]

    def test_view_form(self):
        for lang in self.view_page.form['title']:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(
                    self,
                    user=self.user if self.view_page.redirects_unauthenticated else None,
                    reuse_for_lang=lang)
                assert 'object' in page.form
                # Verify that the expected form class is in use on the view.
                self.assertIsNotNone(page.form['object'])
                self.assertIsInstance(page.form['object'], page.form_class)
                # Verify the expected title of the form.
                self.assertEqual(page.get_form_title(), page.form['title'][lang])
