from unittest.mock import Mock

from django.db.models import Q
from django.test import TestCase, tag

from hosting.filters.search import (
    ModelMultipleChoiceExcludeFilter, NumberOrNoneFilter,
)


@tag('search', 'filters')
class NumberOrNoneFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.queryset = Mock(spec=['filter', 'exclude', 'distinct', 'query'])
        cls.queryset.filter.return_value = cls.queryset
        cls.queryset.exclude.return_value = cls.queryset
        cls.queryset.distinct.return_value = cls.queryset

    def test_init(self):
        f = NumberOrNoneFilter(field_name='dummy_field')
        self.assertEqual(f.lookup_expr, 'exact')
        self.assertFalse(f.exclude)

    def test_filter_empty_value(self):
        f = NumberOrNoneFilter(field_name='dummy_field')

        self.queryset.reset_mock()
        f.filter(self.queryset, '')
        self.queryset.filter.assert_not_called()
        self.queryset.exclude.assert_not_called()

        self.queryset.reset_mock()
        f.filter(self.queryset, None)
        self.queryset.filter.assert_not_called()
        self.queryset.exclude.assert_not_called()

    def test_filter(self):
        f = NumberOrNoneFilter(field_name='dummy_field')
        self.queryset.reset_mock()
        f.filter(self.queryset, 0)
        self.queryset.filter.assert_called_once_with(
            Q(dummy_field__exact=0) | Q(dummy_field__isnull=True)
        )
        self.queryset.exclude.assert_not_called()

    def test_filter_distinct(self):
        f = NumberOrNoneFilter(field_name='dummy_field', distinct=True)
        self.queryset.reset_mock()
        f.filter(self.queryset, "dullard")
        self.queryset.distinct.assert_called_once()
        self.queryset.filter.assert_called_once_with(
            Q(dummy_field__exact="dullard") | Q(dummy_field__isnull=True)
        )
        self.queryset.exclude.assert_not_called()

    def test_exclude(self):
        f = NumberOrNoneFilter(field_name='dummy_field', exclude=True)
        self.queryset.reset_mock()
        f.filter(self.queryset, 2)
        self.queryset.exclude.assert_called_once_with(
            Q(dummy_field__exact=2) | Q(dummy_field__isnull=True)
        )
        self.queryset.filter.assert_not_called()

    def test_exclude_distinct(self):
        f = NumberOrNoneFilter(field_name='dummy_field', exclude=True, distinct=True)
        self.queryset.reset_mock()
        f.filter(self.queryset, "ignoramus")
        self.queryset.distinct.assert_called_once()
        self.queryset.exclude.assert_called_once_with(
            Q(dummy_field__exact="ignoramus") | Q(dummy_field__isnull=True)
        )
        self.queryset.filter.assert_not_called()


@tag('search', 'filters')
class ModelMultipleChoiceExcludeFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.queryset = Mock(spec=['filter', 'exclude', 'distinct', 'query'])
        cls.queryset.filter.return_value = cls.queryset
        cls.queryset.exclude.return_value = cls.queryset
        cls.queryset.distinct.return_value = cls.queryset

    def test_init(self):
        f = ModelMultipleChoiceExcludeFilter(field_name='dummy_field')
        self.assertEqual(f.lookup_expr, 'in')
        self.assertTrue(f.exclude)

    def test_filter_empty_value(self):
        f = ModelMultipleChoiceExcludeFilter(field_name='dummy_field')

        self.queryset.reset_mock()
        f.filter(self.queryset, None)
        self.queryset.filter.assert_not_called()
        self.queryset.exclude.assert_not_called()

        self.queryset.reset_mock()
        f.filter(self.queryset, [])
        self.queryset.filter.assert_not_called()
        self.queryset.exclude.assert_not_called()

    def test_filter(self):
        f = ModelMultipleChoiceExcludeFilter(field_name='dummy_field')

        for test_data in [
                ([15], (15,)),
                ("simpleton", ('s', 'i', 'm', 'p', 'l', 'e', 't', 'o', 'n')),
                ({"mannequin"}, ('mannequin',)),
                ([1, 3, 5], (1, 3, 5))]:
            with self.subTest(value=test_data[0]):
                self.queryset.reset_mock()
                f.filter(self.queryset, test_data[0])
                self.queryset.exclude.assert_called_once_with(
                    Q(dummy_field__in=test_data[1])
                )
                self.queryset.filter.assert_not_called()

    def test_filter_distinct(self):
        f = ModelMultipleChoiceExcludeFilter(field_name='dummy_field', distinct=True)
        self.queryset.reset_mock()
        f.filter(self.queryset, [135])
        self.queryset.distinct.assert_called_once()
        self.queryset.exclude.assert_called_once_with(Q(dummy_field__in=(135,)))
        self.queryset.filter.assert_not_called()

        f = ModelMultipleChoiceExcludeFilter(field_name='dummy_field', distinct=False)
        self.queryset.reset_mock()
        f.filter(self.queryset, [136])
        self.queryset.distinct.assert_not_called()
        self.queryset.exclude.assert_called_once_with(Q(dummy_field__in=(136,)))
        self.queryset.filter.assert_not_called()
