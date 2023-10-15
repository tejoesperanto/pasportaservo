from django.test import override_settings, tag
from django.utils import timezone

from django_webtest import WebTest
from faker import Faker

from tests.assertions import AdditionalAsserts
from tests.factories import UserFactory

from ..models import Post, PublishedManager, PublishedQueryset
from .factories import PostFactory


@tag('models', 'blog')
class PostModelTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.faker = Faker()

    @classmethod
    def setUpTestData(cls):
        cls.basic_post = PostFactory()

    def test_field_max_lengths(self):
        self.assertEqual(self.basic_post._meta.get_field('title').max_length, 200)

    def test_field_blanks(self):
        self.assertFalse(self.basic_post._meta.get_field('title').blank)
        self.assertFalse(self.basic_post._meta.get_field('slug').blank)
        self.assertTrue(self.basic_post._meta.get_field('body').blank)
        self.assertTrue(self.basic_post._meta.get_field('description').blank)
        self.assertTrue(self.basic_post._meta.get_field('author').blank)
        self.assertTrue(self.basic_post._meta.get_field('pub_date').blank)

    def test_field_uniqueness(self):
        self.assertTrue(self.basic_post._meta.get_field('slug').unique)

    def test_ordering(self):
        self.assertEqual(self.basic_post._meta.ordering, ['-pub_date', '-created'])

    def test_str(self):
        self.assertEqual(str(self.basic_post), self.basic_post.title)

    def test_repr(self):
        self.assertSurrounding(repr(self.basic_post), "<Post:", ">")

    def test_absolute_url(self):
        expected_urls = {
            'eo': '/blogo/{}/',
            'en': '/blog/{}/',
        }
        for lang in expected_urls:
            with override_settings(LANGUAGE_CODE=lang):
                with self.subTest(LANGUAGE_CODE=lang):
                    self.assertEqual(
                        self.basic_post.get_absolute_url(),
                        expected_urls[lang].format(self.basic_post.slug)
                    )

    def test_save(self):
        SEPARATOR = "----"

        # A blog post containing two non-empty parts separated by dashes is expected to have a description.
        post = PostFactory.build(description="", body="")
        self.assertIsNone(post.pk)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()
        post.save()
        self.assertIsNotNone(post.pk)
        self.assertEqual(post.description, "<p>{}</p>\n".format(post.content.split(SEPARATOR, 1)[0]))
        self.assertEqual(post.body, "<p>{}</p>\n".format(post.content.replace(SEPARATOR, "", 1)))

        # A blog post containing an empty part separated by dashes from a non-empty part is expected
        # to have no description.
        post = PostFactory.build(
            content=f"{SEPARATOR}{self.faker.sentence()}",
            description="", body="")
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()
        post.save()
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "<p>{}</p>\n".format(post.content.replace(SEPARATOR, "", 1)))

        # A blog post containing a non-empty part separated by dashes from an empty part is expected
        # to have a description, equal to body.
        post = PostFactory.build(
            content=f"{self.faker.sentence()}{SEPARATOR}",
            description="", body="")
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()
        post.save()
        assert_content = "<p>{}</p>\n".format(post.content.replace(SEPARATOR, "", 1))
        self.assertEqual(post.description, assert_content)
        self.assertEqual(post.body, assert_content)

        # A blog post containing no dashes is expected to have a description equal to body.
        post = PostFactory.build(
            content=self.faker.sentence(),
            description="", body="")
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()
        post.save()
        assert_content = f"<p>{post.content}</p>\n"
        self.assertEqual(post.description, assert_content)
        self.assertEqual(post.body, assert_content)

    def test_splitter(self):
        SEPARATOR = "----"

        # A blog post with less than or more than 4 dashes (not a content separator) is expected
        # to have a description, equal to body.
        for splitter in ("-"*2, "-"*3, "-"*5, "-"*6):
            post = PostFactory.build(
                content=f"{self.faker.sentence()}{splitter}{self.faker.sentence()}",
                description="", body="")
            self.assertEqual(post.description, "")
            self.assertEqual(post.body, "")
            post.author.save()
            post.save()
            assert_content = f"<p>{post.content}</p>\n"
            with self.subTest(splitter=splitter):
                self.assertEqual(post.description, assert_content)
                self.assertEqual(post.body, assert_content)

        # A blog post with dashes (not a content separator) followed by separator dashes is expected
        # to have a description, containing dashes, and the full body.
        for splitter in ("-"*2, "-"*3, "-"*5, "-"*6):
            post = PostFactory.build(
                content=f"{self.faker.sentence()}{splitter}{self.faker.sentence()}----{self.faker.sentence()}",
                description="", body="")
            self.assertEqual(post.description, "")
            self.assertEqual(post.body, "")
            post.author.save()
            post.save()
            with self.subTest(splitter=splitter):
                self.assertEqual(post.description, "<p>{}</p>\n".format(post.content.rsplit(SEPARATOR, 1)[0]))
                self.assertEqual(post.body, "<p>{}</p>\n".format("".join(post.content.rsplit(SEPARATOR, 1))))

        # A blog post with separator dashes followed by separator dashes is expected
        # to have a description and the full body, containing dashes.
        post = PostFactory.build(
            content=f"{self.faker.sentence()}----{self.faker.sentence()}----{self.faker.sentence()}",
            description="", body="")
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()
        post.save()
        self.assertEqual(post.description, "<p>{}</p>\n".format(post.content.split(SEPARATOR, 1)[0]))
        self.assertEqual(post.body, "<p>{}</p>\n".format("".join(post.content.split(SEPARATOR, 1))))


@tag('blog')
class PublishedManagerTests(WebTest):
    def test_queryset_class(self):
        mgr = Post.objects
        self.assertIsInstance(mgr, PublishedManager)
        self.assertIsInstance(mgr.get_queryset(), PublishedQueryset)

    def test_published_flag(self):
        # A normal blog post with pub_date in the past.
        PostFactory()
        # A blog post with pub_date = None.
        PostFactory(is_published=False)
        # A blog post with pub_date in the future.
        PostFactory(will_be_published=True)

        qs = Post.objects.get_queryset().order_by('id')
        self.assertEqual(len(qs), 3)
        for i, (publish_tag, flag) in enumerate((
                    ("in past", True), ("not published", False), ("in future", False)
                )):
            with self.subTest(published=publish_tag):
                self.assertEqual(qs[i].published, flag)

    def test_has_more_flag(self):
        # A normal blog post with introduction and content.
        PostFactory()
        # A blog post without an introduction.
        PostFactory(content=Faker().text())

        qs = Post.objects.get_queryset().order_by('id')
        self.assertEqual(len(qs), 2)
        for i, flag in enumerate((True, False)):
            with self.subTest(has_more=flag):
                self.assertEqual(qs[i].has_more, flag)

    def test_published(self):
        author = UserFactory(profile=None)
        Post.objects.bulk_create(
            PostFactory.build_batch(2, author=author)
            + PostFactory.build_batch(3, author=author, is_published=False)
            + PostFactory.build_batch(3, author=author, will_be_published=True)
        )
        mgr = Post.objects
        posts = mgr.published()
        this_day = timezone.now()
        self.assertEqual(len(posts), 2)
        for i in range(2):
            with self.subTest(post_date=posts[i].pub_date):
                self.assertLessEqual(posts[i].pub_date, this_day)

    def test_published_with_no_posts(self):
        mgr = Post.objects
        self.assertEqual(len(mgr.published()), 0)

    def test_published_with_future_posts(self):
        author = UserFactory(profile=None)
        Post.objects.bulk_create(
            PostFactory.build_batch(3, author=author, is_published=False)
            + PostFactory.build_batch(3, author=author, will_be_published=True)
        )
        mgr = Post.objects
        self.assertEqual(len(mgr.published()), 0)
