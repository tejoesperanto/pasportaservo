import os
import tempfile
from subprocess import Popen, PIPE

from django.http.response import HttpResponse
from django.views import generic
from django.template import Context
from django.template.loader import get_template


class PDFBookView(generic.TemplateView):
    template_name = 'book/book.tex'
    pdf_file = 'book/templates/book/book.pdf'
    response_class = HttpResponse
    content_type = 'application/pdf'

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['nomo'] = "Pasporta Servo"
        return kwargs

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        response = self.response_class(**response_kwargs)
        pdf = self.generate_pdf(context)
        response.write(pdf)
        return response

    def generate_pdf(self, context):
        template = get_template(self.template_name)
        rendered_tpl = template.render(context).encode('utf-8')
        with tempfile.TemporaryDirectory() as tempdir:
            # Create subprocess, supress output with PIPE and
            # run latex twice to generate the TOC properly.
            for i in range(2):
                process = Popen(
                    ['xelatex', '-output-directory', tempdir],
                    stdin=PIPE,
                    stdout=PIPE,
                )
                process.communicate(rendered_tpl)
            # Finally read the generated pdf.
            with open(os.path.join(tempdir, 'texput.pdf'), 'rb') as f:
                pdf = f.read()
        return pdf

pdf_book = PDFBookView.as_view()
