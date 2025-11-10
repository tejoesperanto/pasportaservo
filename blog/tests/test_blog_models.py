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
        cls.SEPARATOR = "----"

    @classmethod
    def setUpTestData(cls):
        cls.basic_post = PostFactory.create()

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
        self.assertTrue(getattr(self.basic_post._meta.get_field('slug'), 'unique'))

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
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(LANGUAGE_CODE=lang)
            ):
                self.assertEqual(
                    self.basic_post.get_absolute_url(),
                    expected_urls[lang].format(self.basic_post.slug)
                )

    def test_save(self):
        # A blog post containing two non-empty parts separated by dashes is expected
        # to have a description.
        post = PostFactory.build(description="", body="")
        self.assertIsNone(post.pk)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.author.save()  # type: ignore[union-attr]
        post.save()
        self.assertIsNotNone(post.pk)
        self.assertEqual(
            post.description,
            "<p>{}</p>\n".format(post.content.split(self.SEPARATOR, 1)[0]))
        self.assertEqual(
            post.body,
            "<p>{}</p>\n".format(post.content.replace(self.SEPARATOR, "", 1)))

    def test_save_partial(self):
        post = PostFactory.create()
        self.assertNotEqual(post.description, "")
        self.assertNotEqual(post.body, "")

        # Saving fields not related to the blog post's content is expected not to
        # save the full content, the description, or the body to the database.
        post.title, previous_title = "Ĉiuĵaŭda Eĥoŝanĝo!", post.title
        post.content, previous_content = post.content[::-1], post.content
        post.description, previous_description = "", post.description
        post.body, previous_body = "", post.body
        post.save(update_fields=['title'])
        post.refresh_from_db()
        self.assertEqual(post.title, "Ĉiuĵaŭda Eĥoŝanĝo!")
        self.assertEqual(post.content, previous_content)
        self.assertEqual(post.description, previous_description)
        self.assertEqual(post.body, previous_body)

        # Saving the content field is expected to update also the description and
        # the body in the database, and not save the other fields.
        post.title = previous_title
        post.content = post.content[::-1]
        post.description = "=EĤOŜANĜO="
        post.body = "~Eĥoj kaj Ŝanĝoj."
        post.save(update_fields=['content'])
        post.refresh_from_db()
        self.assertEqual(post.title, "Ĉiuĵaŭda Eĥoŝanĝo!")
        self.assertNotEqual(post.content, previous_content)
        self.assertNotEqual(post.description, "=EĤOŜANĜO=")
        self.assertNotEqual(post.description, previous_description)
        self.assertNotEqual(post.body, "~Eĥoj kaj Ŝanĝoj.")
        self.assertNotEqual(post.body, previous_body)

    def test_post_without_author(self):
        post = PostFactory.create(author=None)
        self.assertIsNone(post.author)
        # Verify retrieval from database.
        retrieved_post = Post.objects.get(pk=post.pk)
        self.assertIsNone(retrieved_post.author)

        # Verify cascade of user deletion.
        post = PostFactory.create()
        self.assertIsNotNone(post.author)
        post.author.delete()  # type: ignore[union-attr]
        retrieved_post = Post.objects.filter(pk=post.pk)
        self.assertLength(retrieved_post, 1)
        self.assertIsNone(retrieved_post[0].author)

    def test_split_empty_description(self):
        # A blog post containing an empty part separated by dashes from a non-empty part
        # is expected to have no description.
        post = PostFactory.build(
            content=f"{self.SEPARATOR}{self.faker.sentence()}",
            description="", body="", author=None)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.save()
        self.assertEqual(post.description, "")
        self.assertEqual(
            post.body,
            "<p>{}</p>\n".format(post.content.replace(self.SEPARATOR, "", 1)))

    def test_split_empty_body(self):
        # A blog post containing a non-empty part separated by dashes from an empty part
        # is expected to have a description, equal to body.
        post = PostFactory.build(
            content=f"{self.faker.sentence()}{self.SEPARATOR}",
            description="", body="", author=None)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.save()
        expected_content = "<p>{}</p>\n".format(post.content.replace(self.SEPARATOR, "", 1))
        self.assertEqual(post.description, expected_content)
        self.assertEqual(post.body, expected_content)

    def test_split_using_only_separator(self):
        # A blog post containing only dashes is expected to have empty description and body.
        post = PostFactory.build(
            content=self.SEPARATOR,
            description="", body="", author=None)
        post.save()
        self.assertEqual(
            post.body, "",
            "Body should be empty when content is only a separator.")
        self.assertEqual(
            post.description, "",
            "Description should be empty when content is only a separator.")

    def test_split_without_separator(self):
        # A blog post containing no dashes is expected to have a description equal to body.
        post = PostFactory.build(
            content=self.faker.sentence(),
            description="", body="", author=None)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.save()
        expected_content = f"<p>{post.content}</p>\n"
        self.assertEqual(post.description, expected_content)
        self.assertEqual(post.body, expected_content)

    def test_split_using_incongruent_dashes(self):
        # A blog post with less than or more than 4 dashes (not a content separator)
        # is expected to have a description, equal to body.
        for splitter in ("-"*2, "-"*3, "-"*5, "-"*6):
            post = PostFactory.build(
                content=f"{self.faker.sentence()}{splitter}{self.faker.sentence()}",
                description="", body="", author=None)
            self.assertEqual(post.description, "")
            self.assertEqual(post.body, "")
            post.save()
            assert_content = f"<p>{post.content}</p>\n"
            with self.subTest(splitter=splitter):
                self.assertEqual(post.description, assert_content)
                self.assertEqual(post.body, assert_content)

    def test_split_using_dashes_and_separator(self):
        # A blog post with dashes (not a content separator) followed by separator dashes
        # is expected to have a description, containing dashes, and the full body.
        for splitter in ("-"*2, "-"*3, "-"*5, "-"*6):
            post = PostFactory.build(
                content=(
                    f"{self.faker.sentence()}{splitter}{self.faker.sentence()}"
                    f"{self.SEPARATOR}{self.faker.sentence()}"
                ),
                description="", body="", author=None)
            self.assertEqual(post.description, "")
            self.assertEqual(post.body, "")
            post.save()
            with self.subTest(splitter=splitter):
                self.assertEqual(
                    post.description,
                    "<p>{}</p>\n".format(post.content.rsplit(self.SEPARATOR, 1)[0]))
                self.assertEqual(
                    post.body,
                    "<p>{}</p>\n".format("".join(post.content.rsplit(self.SEPARATOR, 1))))

    def test_split_using_separator_twice(self):
        # A blog post with separator dashes followed by separator dashes is expected
        # to have a description and the full body, containing dashes.
        post = PostFactory.build(
            content=(
                f"{self.faker.sentence()}{self.SEPARATOR}{self.faker.sentence()}"
                f"{self.SEPARATOR}{self.faker.sentence()}"
            ),
            description="", body="", author=None)
        self.assertEqual(post.description, "")
        self.assertEqual(post.body, "")
        post.save()
        self.assertEqual(
            post.description,
            "<p>{}</p>\n".format(post.content.split(self.SEPARATOR, 1)[0]))
        self.assertEqual(
            post.body,
            "<p>{}</p>\n".format("".join(post.content.split(self.SEPARATOR, 1))))


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
