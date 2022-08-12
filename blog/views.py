from django.contrib.syndication.views import Feed
from django.urls import reverse_lazy
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import gettext_lazy as _
from django.views import generic

from .models import Post


class PostListView(generic.ListView):
    queryset = Post.objects.published().defer('content', 'body')


class PostDetailView(generic.DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = self.model.objects.all()
        context['previous_post'] = posts.filter(pk__lt=self.object.pk).published().first()
        context['next_post'] = posts.filter(pk__gt=self.object.pk).published().last()
        return context


class PostsFeed(Feed):
    title = "Pasporta Servo"
    link = reverse_lazy('blog:posts')
    description = _("The last news about Pasporta Servo")

    def items(self):
        return Post.objects.published()[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_pubdate(self, item):
        return item.pub_date


class PostsAtomFeed(PostsFeed):
    feed_type = Atom1Feed
    subtitle = PostsFeed.description
