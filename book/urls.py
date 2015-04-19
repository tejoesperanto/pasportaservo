from django.conf.urls import patterns, include, url

urlpatterns = patterns('book.views',
    url(r'^$', 'book', name='book'),
)
