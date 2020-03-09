from django.urls import reverse

from django_webtest import WebTest

from .factories import PostFactory


class PostViewTests(WebTest):
    def test_prev_next(self):
        post = PostFactory()
        url = reverse('blog:post', kwargs={"slug": post.slug})
        self.app.get(url, status=200)
