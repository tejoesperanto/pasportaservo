import string

from django.contrib.auth.models import AnonymousUser
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, tag

from hosting.models import Place

from ..factories import PlaceFactory, UserFactory


@tag('templatetags', 'privacy')
class IfVisibleTagTests(TestCase):
    memo_template_string = string.Template(
        "{% load if-visible from privacy %}"
        "{% if-visible obj $SUBOBJ privileged=trusted_user $STORE %}"
        "   {% firstof None 0.0 'Yes' %} "
        "{% endif %}"
        "{{ shall_display_$VARNAME }}"
    )
    template_string = string.Template(
        memo_template_string.safe_substitute(STORE='', VARNAME='')
    )

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create(profile=None)
        cls.trusted_user = UserFactory.create(profile=None)

        test_data = [
            ('public', {'online_public': True, 'online_authed': True}),
            ('restricted', {'online_public': False, 'online_authed': True}),
            ('private', {'online_public': False, 'online_authed': False}),
        ]
        cls.public_place: Place         # noqa: B032
        cls.restricted_place: Place     # noqa: B032
        cls.private_place: Place        # noqa: B032
        cls.all_places: dict[str, Place] = {}
        for place_type, place_vis in test_data:
            place = PlaceFactory.create(
                self_visibility=place_vis,
                visibility_value__field_name='family_members', visibility_value=place_vis)
            setattr(cls, f'{place_type}_place', place)
            cls.all_places[place_type] = place

    def test_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template("{% load if-visible from privacy %}{% if-visible %}")
        self.assertEqual(
            str(cm.exception),
            "Unclosed tag on line 1: 'if-visible'. Looking for one of: endif."
        )

        invalid_templates = [
            "{% if-visible %}{% endif %}",
            "{% if-visible phone privileged %}{% endif %}",
            "{% if-visible phone asvar store %}{% endif %}",
        ]
        for template in invalid_templates:
            with self.subTest(template=template):
                with self.assertRaises(TemplateSyntaxError) as cm:
                    Template("{% load if-visible from privacy %}" + template)
                self.assertIn("Incorrectly provided arguments", str(cm.exception))

    def test_any_object_unauthenticated(self, subobject: str | None = None):
        # When rendering context does not contain a user object or the user is not
        # authenticated (anonymous), the `if` is expected to always result in False.
        template = Template(self.template_string.substitute(
            SUBOBJ='' if not subobject else f'[{subobject}]'
        ))
        context = Context()
        for user_tag in ("none", "anonymous"):
            for place_tag, place in self.all_places.items():
                context['obj'] = place
                with self.subTest(place=place_tag, user=user_tag):
                    if subobject:
                        self.assertTrue(hasattr(place, subobject))
                    page = template.render(context)
                    self.assertEqual(page, "")
            context['user'] = AnonymousUser()

    def object_visibility_tests(
            self, parent_object, sub_object: str | None,
            expected_public: bool, expected_restricted: bool,
    ):
        template = Template(self.template_string.substitute(
            SUBOBJ='' if not sub_object else f'[{sub_object}]'
        ))
        visibility = getattr(
            parent_object,
            (f'{sub_object}_' if sub_object else '') + 'visibility')

        self.assertIs(visibility['online_public'], expected_public)
        page = template.render(Context({'obj': parent_object, 'user': self.user}))
        self.assertEqual(page.strip(), "Yes" if expected_public else "")

        self.assertIs(visibility['online_authed'], expected_restricted)
        page = template.render(Context({
            'obj': parent_object,
            'user': self.trusted_user,
            'trusted_user': True,
        }))
        self.assertEqual(page.strip(), "Yes" if expected_restricted else "")

    def test_public_object_authenticated(self, subobject: str | None = None):
        # For a publicly visible object, the `if` is expected to result in True.
        self.object_visibility_tests(self.public_place, subobject, True, True)

    def test_restricted_object_authenticated(self, subobject: str | None = None):
        # For a privately visible object, the `if` is expected to result in False
        # when the user is not authorized; in True when the user has a privilege
        # (e.g., authorized, supervisor, etc.)
        self.object_visibility_tests(self.restricted_place, subobject, False, True)

    def test_private_object_authenticated(self, subobject: str | None = None):
        # For a hidden object, the `if` is expected to result in False when the
        # user is not authorized and the same even when the user has a privilege.
        self.object_visibility_tests(self.private_place, subobject, False, False)

    def test_subobject_invalid_attribute(self):
        test_data = [
            (False, '[test_one|default:test_two]'),
            (False, '[test_three|capfirst]'),
            (False, '[test_four|upper|default_if_none:False]'),
            (True, '[dummy]'),
            (True, '[test_five|first|escape|default:"dummy"]'),
            (True, '[humpty.d]'),
            (False, '[humpty.e]'),
        ]
        for expected_resolved, subobject_spec in test_data:
            with self.subTest(subobject=subobject_spec):
                template = Template(self.template_string.substitute(SUBOBJ=subobject_spec))
                with self.assertRaises(AttributeError) as cm:
                    template.render(Context({
                        'obj': self.public_place,
                        'user': self.user,
                        'humpty': {'d': "dummy"},
                    }))
                if not expected_resolved:
                    self.assertIn(
                        "did not resolve to any name of attribute",
                        str(cm.exception)
                    )
                else:
                    self.assertEqual(
                        str(cm.exception),
                        "'Place' object has no attribute 'dummy_visibility'"
                    )

    def test_subobject_unauthenticated(self):
        self.test_any_object_unauthenticated('family_members')

    def test_public_subobject_authenticated(self):
        self.test_public_object_authenticated('family_members')

    def test_restricted_subobject_authenticated(self):
        self.test_restricted_object_authenticated('family_members')

    def test_private_subobject_authenticated(self):
        self.test_private_object_authenticated('family_members')

    def test_object_result_memo(self, subobject: str | None = None):
        varname = 'place' if not subobject else subobject
        template = Template(self.memo_template_string.substitute(
            SUBOBJ='' if not subobject else f'[{subobject}]',
            STORE='store',
            VARNAME=varname,
        ))
        # Result for a non-authenticated user is expected to be False.
        context = Context({'obj': self.public_place})
        page = template.render(context)
        self.assertEqual(page, "")
        # Result for an authenticated user accessing a publicly visible
        # object is expected to be memoized as True.
        context['user'] = self.user
        page = template.render(context)
        self.assertIn(f'shall_display_{varname}', context)
        self.assertEqual(page.strip(), "Yes True")
        # Result for an authenticated user accessing a hidden object
        # is expected to be memoized as False.
        context = Context({'obj': self.private_place, 'user': self.user})
        page = template.render(context)
        self.assertIn(f'shall_display_{varname}', context)
        self.assertEqual(page.strip(), "False")

    def test_subobject_result_memo(self):
        self.test_object_result_memo('family_members')
