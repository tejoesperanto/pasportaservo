import string

from django.template import Context, Template
from django.test import TestCase, tag

from ..assertions import AdditionalAsserts


@tag('templatetags')
class CdnTagTests(AdditionalAsserts, TestCase):
    cdn_base = 'https://cdn.jsdelivr.net/'

    def test_base(self):
        page = Template("{% load cdn %}{% cdn %}").render(Context())
        self.assertEqual(page, self.cdn_base)

        page = Template("{% load cdn %}{% cdn version=1.2.3 %}").render(Context())
        self.assertEqual(page, self.cdn_base)

    def test_ps_cdn(self):
        expected_url = 'gh/tejoesperanto/pasportaservo@prod'

        page = Template("{% load cdn %}{% cdn 'ps' %}").render(Context())
        self.assertEqual(page, '{}{}'.format(self.cdn_base, expected_url))

        page = Template("{% load cdn %}{% cdn 'ps' '1.2.3' %}").render(Context())
        self.assertEqual(page, '{}{}'.format(self.cdn_base, expected_url))

        page = Template("{% load cdn %}{% cdn version='1.2.3' library='ps' %}").render(Context())
        self.assertEqual(page, '{}{}'.format(self.cdn_base, expected_url))

    def test_library_cdn(self):
        test_data = {
            'jquery': '/jquery/jquery',
            'bootstrap': '/twbs/bootstrap',
        }
        template_string = string.Template("{% load cdn %}{% cdn '$LIB' $VER %}")
        for library, path in test_data.items():
            for version in (None, 12.3, 'alpha', '77p1-dev4'):
                with self.subTest(library=library, version=version):
                    template = Template(template_string.substitute(
                        LIB=library,
                        VER='"{}"'.format(version) if isinstance(version, str) else (version or '')
                    ))
                    page = template.render(Context())
                    self.assertSurrounding(page, prefix=self.cdn_base)
                    self.assertIn(path + ('@' if version else '/'), page)
                    if version is not None:
                        self.assertIn('@{}'.format(version), page)

    def test_unknown_library(self):
        page = Template("{% load cdn %}{% cdn 'qwerty' %}").render(Context())
        self.assertEqual(page, "")
        page = Template("{% load cdn %}{% cdn 'qwerty' '999.88.7' %}").render(Context())
        self.assertEqual(page, "")
        page = Template("{% load cdn %}{% cdn '999.88.7' %}").render(Context())
        self.assertEqual(page, "")
        page = Template("{% load cdn %}{% cdn version='999.88.7' library='asdf' %}").render(Context())
        self.assertEqual(page, "")
