from unittest.mock import Mock, call

from django.db.models import Q
from django.test import TestCase, tag

from hosting.fields import MultiNullBooleanFormField
from hosting.filters.search import (
    ModelMultipleChoiceExcludeFilter,
    ModelMultipleChoiceIncludeExcludeFilter, NumberOrNoneFilter,
)

from .factories import GenderFactory


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


@tag('search', 'filters')
class ModelMultipleChoiceIncludeExcludeFilterTests(TestCase):
    BOOLEAN_CHOICES = [('true', "hij"), ('false', "klm"), ('unknown', "nop")]

    @classmethod
    def setUpTestData(cls):
        cls.queryset = Mock(spec=['filter', 'exclude', 'distinct', 'query'])
        cls.queryset.filter.return_value = cls.queryset
        cls.queryset.exclude.return_value = cls.queryset
        cls.queryset.distinct.return_value = cls.queryset

        GenderFactory.create_batch(5)
        cls.model = GenderFactory._meta.model
        cls.model_all_objects = cls.model.objects.all()

    def test_init(self):
        f = ModelMultipleChoiceIncludeExcludeFilter(self.BOOLEAN_CHOICES, field_name='dummy_field')
        self.assertEqual(f.lookup_expr, 'exact')
        self.assertTrue(f.distinct)

    def test_field(self):
        f = ModelMultipleChoiceIncludeExcludeFilter(
            self.BOOLEAN_CHOICES, queryset=self.model.objects, field_name='dummy_field')
        self.assertIsInstance(f.field, MultiNullBooleanFormField)
        self.assertEqual(f.field.label, None)
        for i, w in enumerate(f.field.widget.widgets):
            self.assertEqual(w.label, str(self.model_all_objects[i]))
            self.assertIsNone(w.label_prefix)
            self.assertEqual(w.choices, self.BOOLEAN_CHOICES)

    def test_field_labelling(self):
        f = ModelMultipleChoiceIncludeExcludeFilter(
            self.BOOLEAN_CHOICES, queryset=self.model.objects, field_name='dummy_field')
        f.model = self.model
        self.assertEqual(f.field.label, "[invalid name]")

        f = ModelMultipleChoiceIncludeExcludeFilter(
            self.BOOLEAN_CHOICES, queryset=self.model.objects, field_name='name_en')
        f.model = self.model
        self.assertEqual(
            f.field.label.upper(),
            self.model._meta.get_field('name_en').verbose_name.upper())
        for w in f.field.widget.widgets:
            self.assertIsNone(w.label_prefix)

        f = ModelMultipleChoiceIncludeExcludeFilter(
            self.BOOLEAN_CHOICES, queryset=self.model.objects, field_name='name_en',
            label_prefix=lambda choice: choice.instance.name_en[0].upper())
        f.model = self.model
        for i, w in enumerate(f.field.widget.widgets):
            self.assertEqual(w.label_prefix, self.model_all_objects[i].name_en[0].upper())

    def test_filter_empty_value(self):
        f = ModelMultipleChoiceIncludeExcludeFilter(self.BOOLEAN_CHOICES, field_name='dummy_field')
        self.queryset.reset_mock()
        f.filter(self.queryset, [])
        self.queryset.filter.assert_not_called()
        self.queryset.exclude.assert_not_called()

    def test_filter(self):
        f = ModelMultipleChoiceIncludeExcludeFilter(self.BOOLEAN_CHOICES, field_name='dummy_field')

        self.queryset.reset_mock()
        f.filter(self.queryset, [(1, True), (3, False), (5, None), (7, None)])
        self.queryset.exclude.assert_called_once_with(Q(dummy_field__in=(3, )))
        self.queryset.filter.assert_called_once_with(dummy_field=1)

        self.queryset.reset_mock()
        f.filter(self.queryset, [(1, True), (3, False), (2, True), (5, None), (4, False)])
        self.queryset.exclude.assert_called_once_with(Q(dummy_field__in=(3, 4)))
        self.queryset.filter.assert_has_calls(
            [call(dummy_field=2), call(dummy_field=1)],
            any_order=True)

        f = ModelMultipleChoiceIncludeExcludeFilter(self.BOOLEAN_CHOICES, field_name='id')
        odd_objects = [obj.id for obj in self.model_all_objects if obj.id % 2]
        even_objects = [obj.id for obj in self.model_all_objects if obj.id % 2 == 0]

        query = [(id, False) for id in odd_objects][:-1]
        result = f.filter(self.model.objects, query)
        self.assertQuerysetEqual(
            result, even_objects + [odd_objects[-1]], lambda o: o.pk, ordered=False)

        query += [(even_objects[1], True)]
        result = f.filter(self.model.objects, query)
        self.assertQuerysetEqual(result, [even_objects[1]], lambda o: o.pk)

        query += [(odd_objects[-1], True)]
        result = f.filter(self.model.objects, query)
        self.assertQuerysetEqual(result, [])
