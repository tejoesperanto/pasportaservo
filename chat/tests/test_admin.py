import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from postman.models import STATUS_PENDING, PendingMessage

from chat.apps import notify_pending_messages
from tests.assertions import AdditionalAsserts

from .factories import ChatMessageFactory, UserFactory

User = get_user_model()


class NotifyPendingMessagesTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sender = UserFactory.create(profile=None)
        cls.recipient = UserFactory.create(profile=None)

    def test_no_pending_messages(self):
        """
        Tests that no email is sent when there are no pending chat messages.
        """
        self.assertEqual(PendingMessage.objects.count(), 0)
        notify_pending_messages()
        self.assertEqual(len(mail.outbox), 0)

    def test_pending_messages_notification(self):
        """
        Tests that an email is sent to the admins regarding pending chat messages.
        """
        num_messages = random.randint(2, 6)
        ChatMessageFactory.create_batch(
            num_messages,
            sender=self.sender, recipient=self.recipient, moderation_status=STATUS_PENDING)

        expected_content = {
            'en': {
                'subject': f'Note to admin: There are currently {num_messages} chat '
                           + 'messages pending moderation.',
                'body': '/management/postman/pendingmessage/',
            },
            'eo': {
                'subject': f'Sciigo al admino: {num_messages} mesaĝoj atendas permanan '
                           + 'kontrolon.',
                'body': '/administrilo/postman/pendingmessage/',
            },
        }

        for n, lang in enumerate(expected_content, start=1):
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang),
            ):
                notify_pending_messages()

                self.assertEqual(len(mail.outbox), n)
                email = mail.outbox[-1]
                self.assertEndsWith(mail.outbox[-1].subject, expected_content[lang]['subject'])
                self.assertIn(
                    f'//testserver{expected_content[lang]['body']}',
                    mail.outbox[-1].body
                )
                self.assertEqual(email.to, [admin_email for _, admin_email in settings.ADMINS])
