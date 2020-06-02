from unittest import expectedFailure

from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from faker import Faker
from postman.models import Message

from pasportaservo.forms import (
    CustomAnonymousWriteForm, CustomQuickReplyForm,
    CustomReplyForm, CustomWriteForm,
)

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


@tag('forms')
@override_settings(LANGUAGE_CODE='en')
class WriteFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.sender = UserFactory()
        cls.recipient = UserFactory(deceased_user=True)
        cls.faker = Faker()

    def test_init(self):
        form_empty = CustomWriteForm()
        expected_fields = [
            'recipients',
            'subject',
            'body',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))
        # verify that the user filter is defined.
        self.assertTrue(hasattr(form_empty.fields['recipients'], 'user_filter'))
        self.assertIsNotNone(form_empty.fields['recipients'].user_filter)

    def test_clean_recipients(self):
        faker = self.faker

        # Writing to a deceased user is expected to raise an error.
        form = CustomWriteForm(
            sender=self.sender,
            data={'recipients': self.recipient.username, 'subject': faker.sentence(), 'body': faker.paragraph()})
        self.assertFalse(form.is_valid())
        self.assertIn('recipients', form.errors)
        self.assertEndsWith(form.errors['recipients'][0], "This user has passed away.")

        # Writing to a user who is alive is expected to result in no errors.
        form = CustomWriteForm(
            sender=self.recipient,
            data={'recipients': self.sender.username, 'subject': faker.sentence(), 'body': faker.paragraph()})
        self.assertTrue(form.is_valid())

        # Writing to a user without profile is expected to result in no errors.
        form = CustomWriteForm(
            sender=self.sender,
            data={'recipients': UserFactory(profile=None), 'subject': faker.sentence(), 'body': faker.paragraph()})
        self.assertTrue(form.is_valid())

    def test_view_page(self):
        page = self.app.get(reverse('postman:write'), user=self.sender)
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], CustomWriteForm)

    def do_test_form_submit(self, deceased):
        page = self.app.get(reverse('postman:write'), user=self.sender, headers={'Referer': '/origin'})
        page.form['recipients'] = self.recipient.username if deceased else self.sender.username
        page.form['body'] = self.faker.paragraphs()
        page.form['subject'] = self.faker.sentence(nb_words=10)
        page_result = page.form.submit()

        if deceased:
            self.assertEqual(page_result.status_int, 200)
            self.assertFormError(
                page_result,
                'form', 'recipients',
                "Cannot send the message: This user has passed away.")
            self.assertEqual(len(mail.outbox), 0)
        else:
            self.assertEqual(page_result.status_int, 302)
            self.assertRedirects(page_result, '/origin', fetch_redirect_response=False)
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, [self.sender.email])
            self.assertEndsWith(mail.outbox[0].subject, page.form['subject'].value)

    def test_form_submit_living(self):
        self.do_test_form_submit(deceased=False)

    def test_form_submit_deceased(self):
        self.do_test_form_submit(deceased=True)


@tag('forms')
@override_settings(LANGUAGE_CODE='en')
class AnonymousWriteFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.recipient_deceased = UserFactory(deceased_user=True)
        cls.recipient_living = UserFactory()

    def test_init(self):
        form_empty = CustomAnonymousWriteForm()
        expected_fields = [
            'recipients',
            'subject',
            'body',
            'email',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))
        # verify that the user filter is defined.
        self.assertTrue(hasattr(form_empty.fields['recipients'], 'user_filter'))
        self.assertIsNotNone(form_empty.fields['recipients'].user_filter)

    def test_clean_recipients(self):
        faker = Faker()

        # Writing to a deceased user is expected to raise an error.
        form = CustomAnonymousWriteForm(
            sender=AnonymousUser(),
            data={
                'recipients': self.recipient_deceased.username,
                'subject': faker.sentence(),
                'body': faker.paragraph(),
                'email': faker.email(),
            })
        self.assertFalse(form.is_valid())
        self.assertIn('recipients', form.errors)
        self.assertEqual(
            form.errors['recipients'],
            ["Some usernames are rejected: {}.".format(self.recipient_deceased.username)]
        )

        # Writing to a user who is alive is expected to result in no errors.
        form = CustomAnonymousWriteForm(
            sender=AnonymousUser(),
            data={
                'recipients': self.recipient_living.username,
                'subject': faker.sentence(),
                'body': faker.paragraph(),
                'email': faker.email(),
            })
        self.assertTrue(form.is_valid())

        # Writing to a user without profile is expected to result in no errors.
        form = CustomAnonymousWriteForm(
            sender=AnonymousUser(),
            data={
                'recipients': UserFactory(profile=None),
                'subject': faker.sentence(),
                'body': faker.paragraph(),
                'email': faker.email(),
            })
        self.assertTrue(form.is_valid())

    @expectedFailure
    def test_view_page(self):
        # We do not implement a facility for anonymous users to contact registered users currently.
        raise NotImplementedError


@tag('forms')
@override_settings(LANGUAGE_CODE='en')
class ReplyFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.sender = UserFactory()
        cls.recipient = rec = UserFactory(deceased_user=True)
        cls.recipient_other = rec_other = UserFactory(profile=None)
        cls.faker = Faker('el-GR')
        cls.message, cls.message_other = (cls._setup_test_message(u) for u in [rec, rec_other])

    @classmethod
    def _setup_test_message(cls, sender):
        message = Message(
            subject=cls.faker.sentence(),
            body=cls.faker.paragraph(),
            sender=sender,
            recipient=cls.sender,
        )
        message.auto_moderate([])
        message.save()
        return message

    def test_init(self):
        # Verify that the expected fields are part of the full reply form.
        self.assertEqual(set(['subject', 'body']), set(CustomReplyForm().fields))
        # Verify that the expected fields are part of the quick reply form.
        self.assertEqual(set(['body']), set(CustomQuickReplyForm().fields))

    def test_clean_form(self):
        form_test_data = {
            'subject': "RE: {}".format(self.message.subject),
            'body': self.faker.paragraph(),
        }

        # A missing recipient is expected to raise an error.
        for form_class in (CustomReplyForm, CustomQuickReplyForm):
            for originator in (self.sender, self.recipient, self.recipient_other):
                with self.subTest(form_class=form_class.__name__, sender=originator.username):
                    form = form_class(sender=originator, data=form_test_data)
                    self.assertFalse(form.is_valid())
                    self.assertEqual(form.non_field_errors(), ["Undefined recipient."])

        # A deceased recipient is expected to raise an error.
        for form_class in (CustomReplyForm, CustomQuickReplyForm):
            for originator in (self.sender, self.recipient, self.recipient_other):
                with self.subTest(form_class=form_class.__name__, sender=originator.username):
                    form = form_class(sender=originator, recipient=self.recipient, data=form_test_data)
                    self.assertFalse(form.is_valid())
                    self.assertEndsWith(form.non_field_errors()[0], "This user has passed away.")

        # An alive recipient is expected to result in no errors.
        for form_class in (CustomReplyForm, CustomQuickReplyForm):
            for originator in (self.recipient, self.recipient_other):
                with self.subTest(form_class=form_class.__name__, sender=originator.username):
                    form = form_class(sender=originator, recipient=self.sender, data=form_test_data)
                    self.assertTrue(form.is_valid())
                    self.assertEqual(form.errors, {})

        # A recipient without profile is expected to result in no errors.
        for form_class in (CustomReplyForm, CustomQuickReplyForm):
            for destination in (self.recipient_other, AnonymousUser()):
                with self.subTest(form_class=form_class.__name__,
                                  recipient=destination.username or destination.__class__.__name__):
                    form = form_class(sender=self.sender, recipient=destination, data=form_test_data)
                    self.assertTrue(form.is_valid())
                    self.assertEqual(form.errors, {})

    def test_view_page(self):
        for view_name, form_class in (('postman:view', CustomQuickReplyForm),
                                      ('postman:reply', CustomReplyForm)):
            page = self.app.get(reverse(view_name, kwargs={'message_id': self.message.pk}), user=self.sender)
            self.assertEqual(page.status_int, 200)
            self.assertEqual(len(page.forms), 1)
            self.assertIsInstance(page.context['form'], form_class)

    def do_test_form_submit(self, deceased):
        test_views = [
            ('postman:view', CustomQuickReplyForm),
            ('postman:reply', CustomReplyForm),
        ]
        for i, (view_name, form_class) in enumerate(test_views, start=1):
            with self.subTest(form_class=form_class.__name__):
                reply_to_message_id = self.message.pk if deceased else self.message_other.pk
                page = self.app.get(
                    reverse('postman:reply', kwargs={'message_id': reply_to_message_id}),
                    user=self.sender,
                    headers={'Referer': '/origin'})
                page.form['body'] = self.faker.paragraphs()
                page_result = page.form.submit()

                if deceased:
                    self.assertEqual(page_result.status_int, 200)
                    self.assertFormError(
                        page_result,
                        'form', None,
                        "Cannot send the message: This user has passed away.")
                    self.assertEqual(len(mail.outbox), 0)
                else:
                    self.assertEqual(page_result.status_int, 302)
                    self.assertRedirects(page_result, '/origin', fetch_redirect_response=False)
                    self.assertEqual(len(mail.outbox), i)
                    self.assertEqual(mail.outbox[0].to, [self.message_other.sender.email])
                    self.assertEndsWith(mail.outbox[0].subject, page.form['subject'].value)

    def test_form_submit_living(self):
        self.do_test_form_submit(deceased=False)

    def test_form_submit_deceased(self):
        self.do_test_form_submit(deceased=True)
