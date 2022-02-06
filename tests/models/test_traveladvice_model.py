import random
from datetime import date

from django.test import tag

from django_countries import Countries
from django_webtest import WebTest
from factory import Faker

from hosting.managers import ActiveStatusManager
from hosting.models import TravelAdvice

from ..assertions import AdditionalAsserts
from ..factories import TravelAdviceFactory


@tag('models')
class TravelAdviceModelTests(AdditionalAsserts, WebTest):
    def test_field_blanks(self):
        advice = TravelAdviceFactory.build()
        self.assertFalse(advice._meta.get_field('content').blank)
        self.assertFalse(advice._meta.get_field('description').blank)
        self.assertTrue(advice._meta.get_field('countries').blank)
        self.assertTrue(advice._meta.get_field('active_from').blank)
        self.assertTrue(advice._meta.get_field('active_until').blank)

    def test_active_status_flag(self):
        advice = TravelAdviceFactory()
        self.assertTrue(hasattr(TravelAdvice.objects.get(pk=advice.pk), 'is_active'))

    def test_applicable_countries(self):
        # An advice applicable for any country is expected to return the "ALL" label.
        advice = TravelAdviceFactory(countries=[])
        self.assertEqual(
            advice.applicable_countries(all_label=None),
            advice._meta.get_field('countries').blank_label)
        self.assertEqual(advice.applicable_countries(all_label="EVERYONE"), "EVERYONE")
        # An advice for specific countries is expected to return the names or codes of these countries.
        all_world = Countries()
        countries = random.sample(all_world.countries.keys(), 4)
        advice = TravelAdviceFactory(countries=countries)
        self.assertEqual(advice.applicable_countries(code=True), ', '.join(countries))
        self.assertEqual(
            advice.applicable_countries(code=False),
            ', '.join(all_world.name(k) for k in countries)
        )

    def test_trimmed_content(self):
        advice = TravelAdviceFactory(
            content=""
            "We were all feeling seedy, and we were getting quite nervous about it. "
            "Harris said he felt such extraordinary fits of giddiness come over him "
            "at times, that he hardly knew what he was doing.")
        self.assertEqual(advice.trimmed_content(10), "We were ...")
        self.assertEqual(advice.trimmed_content(20), "We were all feelin...")
        self.assertEqual(
            advice.trimmed_content(),
            "We were all feeling seedy, and we were getting quite nervous about i...")
        self.assertEqual(
            TravelAdviceFactory(content="Three invalids.").trimmed_content(),
            "Three invalids.")

    def test_str(self):
        advice = TravelAdviceFactory(content="short message", countries='DD,EE')
        self.assertEqual(str(advice), "short message (DD, EE)")
        advice = TravelAdviceFactory(
            content="quite a long message: with multiple details, spanning several sentences",
            countries='FF')
        self.assertEqual(
            str(advice),
            "quite a long message: with multiple details, spanning several senten... (FF)")

    def test_repr(self):
        # An advice for specific countries is expected to spell out these countries.
        advice = TravelAdviceFactory(countries='AA,BB,CC')
        self.assertSurrounding(repr(advice), "<TravelAdvice for AA, BB, CC:", ">")
        # An advice applicable for any country is expected to spell out "ALL".
        advice = TravelAdviceFactory(countries=[])
        self.assertSurrounding(repr(advice), "<TravelAdvice for ALL:", ">")

    def test_save(self):
        # The advice content is expected to be transformed to a formatted description.
        faker = Faker._get_faker()
        for content in ([faker.sentence()], faker.sentences(2)):
            with self.subTest():
                advice = TravelAdviceFactory.build(description="", content='\n\n'.join(content))
                self.assertIsNone(advice.pk)
                self.assertEqual(advice.description, "")
                advice.save()
                self.assertIsNotNone(advice.pk)
                self.assertEqual(
                    advice.description,
                    "".join("<p>{}</p>\n".format(phrase) for phrase in content)
                )

    def test_get_for_country(self):
        tags = {
            TravelAdviceFactory(countries='AA', in_past=True).pk: 'aa_past',
            TravelAdviceFactory(countries='AA', in_present=True).pk: 'aa_now',
            TravelAdviceFactory(countries='AA', in_future=True).pk: 'aa_future',
            TravelAdviceFactory(countries='', in_past=True).pk: 'any_past',
            TravelAdviceFactory(countries='', in_future=True).pk: 'any_future',
        }
        _tag = lambda advice: tags[advice.pk]
        for country, active, expected in (('BB', True, []),
                                          ('BB', False, []),
                                          ('BB', None, ['any_future', 'any_past']),
                                          ('AA', True, ['aa_now']),
                                          ('AA', False, ['aa_future', 'aa_past'])):
            with self.subTest(country=country, is_active=active):
                self.assertQuerysetEqual(
                    TravelAdvice.get_for_country(country, active), expected, transform=_tag)
        with self.subTest(country='AA', is_active=None):
            self.assertQuerysetEqual(
                TravelAdvice.get_for_country('AA', None), tags.values(), ordered=False, transform=_tag)


@tag('models')
class ActiveStatusManagerTests(WebTest):
    def test_manager_class(self):
        mgr = TravelAdvice.objects
        self.assertIsInstance(mgr, ActiveStatusManager)

    def test_active_status_flag(self):
        faker = Faker._get_faker()
        test_data = [
            (
                "in past", False,
                TravelAdviceFactory(
                    active_from=faker.date_between('-30d', '-15d'),
                    active_until=faker.date_between('-14d', '-2d'))
            ), (
                "in past", False,
                TravelAdviceFactory(
                    active_from=None,
                    active_until=faker.date_between('-30d', '-2d'))
            ), (
                "in future", False,
                TravelAdviceFactory(
                    active_from=faker.date_between('+2d', '+14d'),
                    active_until=faker.date_between('+15d', '+30d'))
            ), (
                "in future", False,
                TravelAdviceFactory(
                    active_from=faker.date_between('+2d', '+30d'),
                    active_until=None)
            ), (
                "in present", True,
                TravelAdviceFactory(
                    active_from=faker.date_between('-30d', '-2d'),
                    active_until=faker.date_between('+2d', '+30d'))
            ), (
                "in present", True,
                TravelAdviceFactory(
                    active_from=faker.date_between('-30d', '-2d'),
                    active_until=faker.date_between('+2d', '+30d'))
            ), (
                "in present", True,
                TravelAdviceFactory(
                    active_from=faker.date_between('-30d', 'today'),
                    active_until=None)
            ), (
                "in present", True,
                TravelAdviceFactory(
                    active_from=None,
                    active_until=faker.date_between('today', '+30d'))
            ), (
                "in present", True,
                TravelAdviceFactory(active_from=None, active_until=None)
            ), (
                "in present", True,
                TravelAdviceFactory(active_from=date.today(), active_until=date.today())
            )
        ]
        qs = TravelAdvice.objects.get_queryset().order_by('id')
        self.assertEqual(len(qs), len(test_data))
        for i, (time_tag, active_flag, advice) in enumerate(test_data):
            with self.subTest(start=str(advice.active_from), stop=str(advice.active_until), era=time_tag):
                self.assertEqual(qs[i].pk, advice.pk)
                self.assertEqual(qs[i].is_active, active_flag)
