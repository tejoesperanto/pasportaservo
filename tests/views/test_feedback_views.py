from typing import Optional, cast
from unittest.mock import DEFAULT as DEFAULT_RETURN_VALUE, MagicMock, patch

from django.conf import settings
from django.core import mail
from django.test import override_settings, tag
from django.urls import reverse_lazy

from django_webtest import WebTest
from faker import Faker
from graphql import GraphQLError

from core.models import FEEDBACK_TYPES
from hosting.models import PasportaServoUser
from tests.factories import UserFactory

from .. import DjangoWebtestResponse
from ..assertions import AdditionalAsserts


@tag('views', 'views-feedback')
@patch('core.views.GQLClient')
class FeedbackViewTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.feedback_type = next(iter(FEEDBACK_TYPES.keys()))
        cls.feedback_url = reverse_lazy('user_feedback')
        cls.faker = Faker()
        cls.user = UserFactory.create(profile=None)

        cls.expected_strings = {
            'en': {
                'comment': {
                    False: f"Sent from the website {settings.ENVIRONMENT} (/)",
                    True: f"Sent from the website {settings.ENVIRONMENT} ({cls.user.pk})",
                },
                'mail_subject': f"Feedback on {FEEDBACK_TYPES[cls.feedback_type].name}.",
                'mail_content': {
                    False: "Anonymous:",
                    True: f"User {cls.user.pk} ({cls.user.username}):",
                },
                'page_title': "Feedback | Pasporta Servo",
                'page_content': {
                    False: "You sent an empty feedback, so we did not register it.",
                    True: "Your feedback was successfully registered. Thank you.",
                    None: "Your feedback could not be registered due to an unexpected error.",
                },
            },
            'eo': {
                'comment': {
                    False: f"Sendita el la retejo {settings.ENVIRONMENT} (/)",
                    True: f"Sendita el la retejo {settings.ENVIRONMENT} ({cls.user.pk})",
                },
                'mail_subject': f"Komento pri {FEEDBACK_TYPES[cls.feedback_type].esperanto_name}.",
                'mail_content': {
                    False: "Anonimo:",
                    True: f"Uzanto {cls.user.pk} ({cls.user.username}):",
                },
                'page_title': "Opinio | Pasporta Servo",
                'page_content': {
                    False: "Vi sendis malplenan komenton, do ni ne registris ĝin.",
                    True: "Via komento estis registrita sukcese. Dankon!",
                    None: "Via komento ne povis esti registrita pro neatendita eraro.",
                },
            },
        }

    def test_get_method(self, mock_gql_client):
        """
        Tests that GET requests to the feedback view are not allowed.
        """
        response: DjangoWebtestResponse = self.app.get(self.feedback_url, expect_errors=True)
        self.assertEqual(response.status_code, 405)

    def submission_scenarios_tests(
            self,
            mock_gql: MagicMock,
            *,
            empty_feedback: bool,
            private_feedback: bool,
            gql_error: bool = False,
    ):
        for user in [None, self.user]:
            for ajax in [True, False]:
                for lang in self.expected_strings:
                    with (
                        override_settings(LANGUAGE_CODE=lang),
                        self.subTest(
                            user="authenticated" if user else "anonymous",
                            ajax=ajax, empty=empty_feedback, lang=lang,
                        )
                    ):
                        wanted_content_type = 'application/json' if ajax else 'text/html'
                        feedback_text = self.faker.sentence() if not empty_feedback else ""
                        self.app.reset()
                        self.app.set_user(user)
                        mock_gql.reset_mock(side_effect=not gql_error)

                        comment_id = self.faker.random_int(10001, 99999)
                        mock_gql.return_value = {
                            'addDiscussionComment': {'comment': {'id': comment_id}}
                        }

                        # Submit the initial comment (it may be empty) and verify the
                        # email to the admins and the response to the user.
                        response = self.valid_submission_tests(
                            lang, user, feedback_text, wanted_content_type,
                            is_ajax=ajax, private_feedback=private_feedback,
                            is_gql_error=gql_error)

                        # When a comment is public and not empty, a GraphQL query is
                        # expected to be sent with the text of the comment.
                        if not private_feedback and not empty_feedback:
                            self.assertEqual(mock_gql.call_count, 1)
                            submitted_values: dict[str, str] = (
                                mock_gql.call_args.kwargs['variable_values']
                            )
                            self.assertIn(feedback_text, submitted_values['body_text'])
                            self.assertIn(
                                self.expected_strings[lang]['comment'][user is not None],
                                submitted_values['body_text'])
                        else:
                            self.assertEqual(mock_gql.call_count, 0)

                        # Submit a comment update with empty text.
                        response = self.valid_submission_tests(
                            lang, user, "", wanted_content_type,
                            previous_page=response,
                            is_ajax=ajax, private_feedback=private_feedback,
                            is_gql_error=gql_error)
                        # No GraphQL query is expected since the comment is empty.
                        self.assertEqual(
                            mock_gql.call_count,
                            1 if not private_feedback and not empty_feedback else 0)

                        # The following scenarios are irrelevant if GQL queries fail.
                        if gql_error:
                            continue

                        # Submit a comment update with with non-empty text.
                        additional_feedback_text = self.faker.sentence()
                        if not empty_feedback:
                            mock_gql.side_effect = [
                                {'node': {'body': feedback_text}},
                                {'updateDiscussionComment': {'comment': {'id': comment_id}}},
                            ]
                        response = self.valid_submission_tests(
                            lang, user, additional_feedback_text, wanted_content_type,
                            previous_page=response,
                            is_ajax=ajax, private_feedback=private_feedback)

                        # When the original comment is public, a GraphQL query is
                        # expected to be sent with the combined previous and updated text
                        # (if the original comment is not empty) or just the new text (if
                        # the original comment is empty, meaning it was not submitted).
                        if not private_feedback:
                            submitted_values = mock_gql.call_args.kwargs['variable_values']
                            if not empty_feedback:
                                self.assertEqual(mock_gql.call_count, 3)
                                self.assertEqual(
                                    submitted_values['body_text'],
                                    f"{feedback_text}\n\n----\n\n{additional_feedback_text}")
                            else:
                                self.assertEqual(mock_gql.call_count, 1)
                                self.assertIn(additional_feedback_text, submitted_values['body_text'])
                        else:
                            self.assertEqual(mock_gql.call_count, 0)

                        # Verify that a GraphQL error on comment retrieval results in
                        # submission of a new comment.
                        mock_gql.side_effect = [
                            GraphQLError("Mock Exception"), DEFAULT_RETURN_VALUE,
                        ]
                        response = self.valid_submission_tests(
                            lang, user, additional_feedback_text, wanted_content_type,
                            previous_page=response,
                            is_ajax=ajax, private_feedback=private_feedback)

                        # When the original comment is public, a GraphQL query is expected
                        # to be sent with just the updated text.
                        if not private_feedback:
                            self.assertEqual(mock_gql.call_count, 5 if not empty_feedback else 3)
                            submitted_values = mock_gql.call_args.kwargs['variable_values']
                            self.assertIn(additional_feedback_text, submitted_values['body_text'])
                            if not empty_feedback:
                                self.assertNotIn(feedback_text, submitted_values['body_text'])
                        else:
                            self.assertEqual(mock_gql.call_count, 0)

    def tampering_scenarios_tests(
        self,
        mock_gql: MagicMock,
        *,
        empty_feedback: bool,
        private_feedback: bool,
    ):
        mock_gql.side_effect = GraphQLError("Unexpected Exception")

        for user in [None, self.user]:
            for ajax in [True, False]:
                for lang in self.expected_strings:
                    with (
                        override_settings(LANGUAGE_CODE=lang),
                        self.subTest(
                            user="authenticated" if user else "anonymous",
                            ajax=ajax, empty=empty_feedback, lang=lang,
                        )
                    ):
                        wanted_content_type = 'application/json' if ajax else 'text/html'
                        if not empty_feedback:
                            feedback_text = (self.faker.sentence(nb_words=10) + " ") * 75
                        else:
                            feedback_text = ""
                        self.app.reset()
                        self.app.set_user(user)
                        mock_gql.reset_mock()

                        # Submit the comment (it may be empty) and an invalid value for
                        # the `feedback_type` parameter. Verify the log and the response
                        # to the user.
                        self.invalid_submission_tests(
                            lang, feedback_text, wanted_content_type,
                            is_ajax=ajax, private_feedback=private_feedback)
                        mock_gql.assert_not_called()

    def valid_submission_tests(
            self,
            lang: str,
            user: PasportaServoUser | None,
            feedback_text: str,
            wanted_content_type: str,
            *,
            is_ajax: bool,
            private_feedback: bool,
            is_gql_error: bool = False,
            previous_page: Optional[DjangoWebtestResponse] = None,
    ) -> DjangoWebtestResponse:
        mail.outbox = []

        response = self.perform_request_and_verify(
            feedback_text, wanted_content_type,
            private_feedback=private_feedback,
            previous_page=previous_page,
        )

        if (not private_feedback and not is_gql_error) or not feedback_text:
            # When the submission is public or empty, no email is expected to be sent
            # to the admins.
            self.assertLength(mail.outbox, 0)
        else:
            # When the private submission is not empty, an email containing the full
            # content of the feedback is expected to be sent to the admins.
            self.assertLength(mail.outbox, 1)
            self.assertEndsWith(
                mail.outbox[0].subject,
                self.expected_strings[lang]['mail_subject'])
            self.assertStartsWith(
                mail.outbox[0].body,
                self.expected_strings[lang]['mail_content'][user is not None])
            self.assertIn(feedback_text, mail.outbox[0].body)
            if not private_feedback and is_gql_error:
                self.assertIn(
                    "During public submission, an exception has occured",
                    mail.outbox[0].body)
            else:
                self.assertNotIn("exception has occured", mail.outbox[0].body)

        self.success_response_tests(lang, response, is_ajax, feedback_text == "")

        return response

    def invalid_submission_tests(
            self,
            lang: str,
            feedback_text: str,
            wanted_content_type: str,
            *,
            is_ajax: bool,
            private_feedback: bool,
    ) -> DjangoWebtestResponse:
        mail.outbox = []

        with self.assertLogs('PasportaServo.ui.feedback', level='ERROR') as log:
            response = self.perform_request_and_verify(
                feedback_text, wanted_content_type,
                feedback_type='invalid_type', private_feedback=private_feedback,
            )

        # No email regarding a successful submission is expected to be sent.
        # Note: the AssertLogs Context Manager disables all existing handlers
        #       of the logger, resulting in no emails being dispatched to the
        #       admins, if configured.
        for message in mail.outbox:
            self.assertNotEqual(
                message.subject,
                self.expected_strings[lang]['mail_subject'])
        # The validation error is expected to be recorded in the log.
        self.assertLength(log.records, 1)
        self.assertIn("Feedback form did not validate correctly", log.output[0])
        self.assertIn(f"Original submission: #{feedback_text[:1000]}#", log.output[0])
        # When the submission is too long, the full text is not supposed
        # to be registered in the log.
        if feedback_text:
            self.assertNotIn(feedback_text, log.output[0])

        self.error_response_tests(lang, response, is_ajax)

        return response

    def perform_request_and_verify(
            self,
            feedback_text: str,
            wanted_content_type: str,
            *,
            private_feedback: bool,
            previous_page: Optional[DjangoWebtestResponse] = None,
            feedback_type: Optional[str] = None,
    ) -> DjangoWebtestResponse:
        if previous_page is None or not previous_page.context:
            previous_page = cast(DjangoWebtestResponse, self.app.get('/'))

        data = {
            'feedback_on': feedback_type if feedback_type is not None else self.feedback_type,
            'message': feedback_text,
            'csrfmiddlewaretoken': previous_page.context['csrf_token'],
        }
        if private_feedback:
            data['private'] = "on"
        if 'csrf' not in self.app.cookies:
            # Needed for the anonymous user.
            self.app.set_cookie('csrftoken', previous_page.context['csrf_token'])
        response: DjangoWebtestResponse = self.app.post(
            self.feedback_url,
            params=data,
            headers={
                'Accept': wanted_content_type,
            },
        )

        # The response is expected to be 200 OK for both valid and invalid submissions,
        # with the suitable content (HTML for a form POST, JSON for an AJAX POST).
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, wanted_content_type)

        return response

    def success_response_tests(
            self,
            lang: str,
            response: DjangoWebtestResponse,
            is_ajax: bool,
            empty_feedback: bool,
    ):
        if is_ajax:
            # For an AJAX POST, the response is expected to be a JSON
            # with two keys (`result` and `submitted`).
            json = response.json
            self.assertTrue(json.get('result'), msg=f'Received response is {json}')
            assertion = self.assertTrue if not empty_feedback else self.assertFalse
            assertion(json.get('submitted'), msg=f'Received response is {json}')
        else:
            # For a regular form POST, the response is expected to be an
            # HTML page informing the user that the submission succeeded.
            self.assertTemplateUsed(response, 'core/feedback_sent.html')
            pyquery = response.pyquery
            self.assertHTMLEqual(
                cast(str, pyquery("title").html()),
                self.expected_strings[lang]['page_title']
            )
            heading_element = pyquery("h1, h2")
            self.assertLength(heading_element, 1)
            self.assertEqual(
                heading_element.eq(0).text(),
                self.expected_strings[lang]['page_content'][not empty_feedback]
            )

    def error_response_tests(
            self,
            lang: str,
            response: DjangoWebtestResponse,
            is_ajax: bool,
    ):
        if is_ajax:
            # For an AJAX POST, the response is expected to be a JSON
            # with a single key (`result`).
            json = response.json
            self.assertFalse(json.get('result'), msg=f'Received response is {json}')
            self.assertIsNone(json.get('submitted'), msg=f'Received response is {json}')
        else:
            # For a regular form POST, the response is expected to be an
            # HTML page informing the user that the submission failed.
            self.assertTemplateUsed(response, 'core/feedback_form_fail.html')
            pyquery = response.pyquery
            self.assertHTMLEqual(
                cast(str, pyquery("title").html()),
                self.expected_strings[lang]['page_title']
            )
            heading_element = pyquery("h1, h2")
            self.assertLength(heading_element, 1)
            self.assertEqual(
                heading_element.eq(0).text(),
                self.expected_strings[lang]['page_content'][None]
            )

    def test_private_feedback(self, mock_gql_client: MagicMock):
        """
        Tests that both anonymous and authenticated users can submit private feedback.
        """
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=True, empty_feedback=False,
        )

    def test_private_empty_feedback(self, mock_gql_client: MagicMock):
        """
        Tests that empty private feedback from both anonymous and authenticated users
        is ignored (not sent to the admins).
        """
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=True, empty_feedback=True,
        )

    def test_private_feedback_gql_error(self, mock_gql_client: MagicMock):
        """
        Tests that a GQL error during private submission does not influence it.
        """
        mock_gql_client.return_value.execute.side_effect = GraphQLError("Mock Exception")
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=True, empty_feedback=False, gql_error=True,
        )

    def test_private_feedback_form_error(self, mock_gql_client: MagicMock):
        """
        Tests that an invalid form submission is handled correctly and that the feedback
        message is truncated in the log.
        """
        self.tampering_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=True, empty_feedback=False,
        )

        self.tampering_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=True, empty_feedback=True,
        )

    def test_public_feedback(self, mock_gql_client: MagicMock):
        """
        Tests that both anonymous and authenticated users can submit public feedback.
        """
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=False, empty_feedback=False,
        )

    def test_public_empty_feedback(self, mock_gql_client: MagicMock):
        """
        Tests that empty public feedback from both anonymous and authenticated users
        is ignored (not sent to the admins).
        """
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=False, empty_feedback=True,
        )

    def test_public_feedback_gql_error(self, mock_gql_client: MagicMock):
        """
        Tests that a GQL error during public submission results in a private submission.
        """
        mock_gql_client.return_value.execute.side_effect = GraphQLError("Mock Exception")
        self.submission_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=False, empty_feedback=False, gql_error=True,
        )

    def test_public_feedback_form_error(self, mock_gql_client: MagicMock):
        """
        Tests that an invalid form submission is handled correctly and that the feedback
        message is truncated in the log.
        """
        self.tampering_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=False, empty_feedback=False,
        )

        self.tampering_scenarios_tests(
            mock_gql_client.return_value.execute,
            private_feedback=False, empty_feedback=True,
        )
