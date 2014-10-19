from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns('pages.views',
    url(_(r'^about/$'), 'about', name='about'),
    url(_(r'^terms-and-conditions/$'), 'terms_conditions', name='terms_conditions'),
)

