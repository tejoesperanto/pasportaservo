from django.urls import path

from .views import PostDetailView, PostListView, PostsAtomFeed, PostsFeed

app_name = 'blog'
urlpatterns = [
    path('rss.xml', PostsAtomFeed(), name='rss'),
    path('atom.xml', PostsFeed(), name='atom'),
    path('<slug:slug>/', PostDetailView.as_view(), name='post'),
    path('', PostListView.as_view(), name='posts'),
]
