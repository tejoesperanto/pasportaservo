from django.views import generic


class AboutView(generic.TemplateView):
    template_name = 'pages/about.html'

about = AboutView.as_view()


class TermsAndConditionsView(generic.TemplateView):
    template_name = 'pages/terms_conditions.html'

terms_conditions = TermsAndConditionsView.as_view()


class SupervisorsView(generic.TemplateView):
    template_name = 'pages/supervisors.html'

supervisors = SupervisorsView.as_view()


class FaqView(generic.TemplateView):
    template_name = 'pages/faq.html'

faq = FaqView.as_view()
