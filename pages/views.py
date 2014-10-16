from django.shortcuts import render
from django.views import generic
from django.conf import settings

lang = settings.LANGUAGE_CODE

class AboutView(generic.TemplateView):
    template_name = 'pages/about.html'
    
about = AboutView.as_view()

class TermsAndConditionsView(generic.TemplateView):
    template_name = 'pages/terms_conditions.html'

terms_conditions = TermsAndConditionsView.as_view()

