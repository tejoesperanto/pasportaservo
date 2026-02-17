from django.test import TestCase, tag
from django.utils import timezone

from faker import Faker
from postman.api import pm_write
from postman.models import STATUS_ACCEPTED, STATUS_PENDING, STATUS_REJECTED

from pasportaservo.views import ExtendedReplyView, ExtendedWriteView
from tests.factories import UserFactory


@tag('chat')
class ModerateWriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = UserFactory.create()
        cls.recipients = UserFactory.create_batch(3, profile=None)
        cls.faker = Faker()

    def test_no_sender(self):
        # A message without a sender is expected to be automatically put in moderation
        # pending status.
        message = pm_write(
            None,  # type: ignore
            self.recipients[0], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_PENDING)

    def test_disabled_sender(self):
        self.author.is_active = False
        self.author.save()
        message = pm_write(
            self.author, self.recipients[1], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_REJECTED)

        self.author.is_active = True
        self.author.set_unusable_password()
        self.author.save()
        message = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_REJECTED)

    def test_pending_messages(self):
        # When the user sends a message after all previous messages were held (pending
        # moderation), or no earlier messages were yet accepted, it is expected to be
        # also held, that is, put in moderation pending status.
        for i, recipient in enumerate(self.recipients):
            with self.subTest(seq=f'#{i + 1}'):
                message = pm_write(
                    self.author, recipient, self.faker.sentence(), self.faker.sentence(),
                    skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
                self.assertEqual(message.moderation_status, STATUS_PENDING)

    def test_rejected_messages(self):
        # Ensure that there is a rejected message for the purpose of the test.
        message_1 = pm_write(
            self.author, self.recipients[0], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=lambda msg: False)
        self.assertEqual(message_1.moderation_status, STATUS_REJECTED)

        # When the user sends a message after all previous messages were rejected,
        # it is expected to be put in moderation pending status.
        message_2 = pm_write(
            self.author, self.recipients[1], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_2.moderation_status, STATUS_PENDING)

        # When the user sends a message after the previous message was accepted,
        # it is expected to be accepted as well, even when there are earlier rejected
        # messages from this user.
        message_2.moderation_status = STATUS_ACCEPTED
        message_2.save()
        message_3 = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_3.moderation_status, STATUS_ACCEPTED)

        # When the user sends a message after the previous message was rejected,
        # it is expected to be put in moderation pending status, even when there are
        # earlier accepted messages from this user.
        message_3.moderation_status = STATUS_REJECTED
        message_3.save()
        message_4 = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_4.moderation_status, STATUS_PENDING)

        # When the user sends a message after the previous message was held (pending
        # moderation), it is expected to be also held, even when there are earlier
        # accepted or rejected messages from this user.
        message_5 = pm_write(
            self.author, self.recipients[1], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_5.moderation_status, STATUS_PENDING)

    def test_sender_without_profile(self):
        author = UserFactory.create(profile=None)

        # The very first message sent by the user is expected to be held (pending
        # moderation), irrespective of whether the user has a profile or not.
        message_1 = pm_write(
            author, self.recipients[0], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_1.moderation_status, STATUS_PENDING)

        # When a user without a profile sends a message, it is expected to be held
        # even if earlier messages were accepted.
        message_1.moderation_status = STATUS_ACCEPTED
        message_1.save()
        message_2 = pm_write(
            author, self.recipients[0], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_2.moderation_status, STATUS_PENDING)
        self.assertTrue(getattr(author, '_profile_examined', None))

    def test_sender_with_changed_profile(self):
        # Ensure that there is an accepted message for the purpose of the test.
        message_1 = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=lambda msg: True)
        self.assertEqual(message_1.moderation_status, STATUS_ACCEPTED)

        # When the user sends a message after an earlier message was accepted and the
        # profile was not changed since then, it is expected to be accepted as well.
        # The moderation function is expected to examine the profile of that user.
        message_2 = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_2.moderation_status, STATUS_ACCEPTED)
        self.assertTrue(getattr(self.author, '_profile_examined', None))

        # When the user sends a message after earlier messages were accepted and the
        # user's profile was changed since then, the moderation function is expected
        # to examine the profile of that user and put the message in moderation
        # pending status.
        setattr(self.author, '_profile_examined', None)
        self.author.profile.personal_details_changed_on = timezone.now()
        self.author.profile.save()
        message_3 = pm_write(
            self.author, self.recipients[2], self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedWriteView.auto_moderators)
        self.assertEqual(message_3.moderation_status, STATUS_PENDING)
        self.assertTrue(getattr(self.author, '_profile_examined', None))


@tag('chat')
class ModerateReplyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.recipient = UserFactory.create(profile=None)
        cls.faker = Faker()

    def test_no_sender(self):
        # A reply message without a sender is expected to be automatically put in
        # moderation pending status.
        message = pm_write(
            None,  # type: ignore
            self.recipient, self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedReplyView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_PENDING)

    def test_disabled_sender(self):
        author = UserFactory.create(is_active=False)
        message = pm_write(
            author, self.recipient, self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedReplyView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_REJECTED)

        author.is_active = True
        author.set_unusable_password()
        author.save()
        message = pm_write(
            author, self.recipient, self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedReplyView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_REJECTED)

    def test_sender_without_profile(self):
        author = UserFactory.create(profile=None)

        # A reply message sent by a user without a profile is expected to be accepted
        # nonetheless (the ability of users without profile to receive messages and
        # reply to them is controlled on view level).
        message = pm_write(
            author, self.recipient, self.faker.sentence(), self.faker.sentence(),
            skip_notification=True, auto_moderators=ExtendedReplyView.auto_moderators)
        self.assertEqual(message.moderation_status, STATUS_ACCEPTED)
        self.assertFalse(getattr(author, '_profile_examined', False))
