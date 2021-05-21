from django.conf.urls import url

from .views import PostDetailView, PostListView, PostsAtomFeed, PostsFeed

app_name = "blog"
urlpatterns = [
    url(r"^rss.xml$", PostsAtomFeed(), name="rss"),
    url(r"^atom.xml$", PostsFeed(), name="atom"),
    url(r"^(?P<slug>[\w-]+)/$", PostDetailView.as_view(), name="post"),
    url(r"^$", PostListView.as_view(), name="posts"),
]
