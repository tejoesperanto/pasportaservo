from django.template import Context, Template
from django.test import TestCase, tag


@tag('templatetags')
class LatexFilterTests(TestCase):
    def test_escape_latex(self):
        template = Template(
            "{% load escape_latex from latex %}"
            "{% autoescape off %}{{ value|escape_latex }}{% endautoescape %}"
        )
        page = template.render(Context({
            'value': "A & B %! _\\- $# <{ \"C' }> ~[^]*",
        }))
        self.assertEqual(
            page,
            r"""A \& B \%! \_\- \$\# <\{ "C' \}> \textasciitilde [\textasciicircum ]*"""
        )

    def test_cmd(self):
        template = Template("{% load cmd from latex %}{{ value|cmd:'section' }}")
        page = template.render(Context({'value': ""}))
        self.assertEqual(page, r"\section{}")
        page = template.render(Context({'value': "Introduction"}))
        self.assertEqual(page, r"\section{Introduction}")

        template = Template("{% load cmd from latex %}{{ value|cmd:'dgspace' }}")
        page = template.render(Context({'value': "6em \\break"}))
        self.assertEqual(page, r"\dgspace{6em \break}")

    def test_ctx(self):
        template = Template("{% load ctx from latex %}{{ value|ctx:'bold,smallcaps' }}")
        page = template.render(Context({'value': "Chapter 2"}))
        self.assertEqual(page, r"{\bold\smallcaps Chapter 2}")

        template = Template("{% load ctx from latex %}{{ value|ctx:'large' }}")
        page = template.render(Context({'value': ""}))
        self.assertEqual(page, r"{\large }")
        page = template.render(Context({'value': "\\item{dot}"}))
        self.assertEqual(page, r"{\large \item{dot}}")

    def test_bracket(self):
        template = Template("{% load bracket from latex %}{{ value|bracket }}")
        page = template.render(Context({'value': ""}))
        self.assertEqual(page, "()")
        page = template.render(Context({'value': "  First (Second$) Third ~"}))
        self.assertEqual(page, "(  First (Second$) Third ~)")

    def test_color(self):
        template = Template("{% load color from latex %}{{ value|color:'amandel' }}")
        page = template.render(Context({'value': ""}))
        self.assertEqual(page, r"\textcolor{amandel}{}")
        page = template.render(Context({'value': "Wel{c}ome"}))
        self.assertEqual(page, r"\textcolor{amandel}{Wel{c}ome}")

        template = Template("{% load color from latex %}{{ value|color:'blue,green' }}")
        page = template.render(Context({'value': "Good#bye"}))
        self.assertEqual(page, r"\textcolor{blue,green}{Good#bye}")

        template = Template("{% load color from latex %}{{ value|color }}")
        page = template.render(Context({'value': "Aů?rěvoïr"}))
        self.assertEqual(page, r"\textcolor{gray}{Aů?rěvoïr}")
