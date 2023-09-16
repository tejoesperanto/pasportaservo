import traceback
from collections.abc import Collection
from typing import Any, Optional
from unittest.case import _AssertRaisesContext
from unittest.util import safe_repr

from django.contrib.gis.geos import Point as GeoPoint
from django.test import TestCase

from bs4 import ResultSet as SoupResultSet, Tag as SoupTag
from pyquery import PyQuery

from maps import SRID

from . import with_type_hint


class AdditionalAsserts(with_type_hint(TestCase)):
    def assertSurrounding(
            self,
            string: Any,
            prefix: Optional[str] = None,
            postfix: Optional[str] = None,
            msg: Optional[str] = None,
    ):
        """
        Asserts that the string has the given prefix and postfix.
        """
        self.assertStartsWith(string, prefix, msg)
        self.assertEndsWith(string, postfix, msg)

    def assertStartsWith(
            self,
            string: Any,
            prefix: Optional[str] = None,
            msg: Optional[str] = None,
    ):
        """
        Asserts that the string has the given prefix.
        """
        if string is not None and not isinstance(string, str):
            self.fail("First argument is not a string")
        if prefix and string is None:
            self.fail(self._formatMessage(
                msg, f"{string} does not start with '{prefix}'"
            ))
        if prefix and not string.startswith(prefix):
            self.fail(self._formatMessage(msg, "'{}' does not start with '{}'".format(
                string[:len(prefix)+8]
                + ("[...]" if len(string) > len(prefix)+10 else string[len(prefix)+8:]),
                prefix
            )))

    def assertEndsWith(
            self,
            string: Any,
            postfix: Optional[str] = None,
            msg: Optional[str] = None,
    ):
        """
        Asserts that the string has the given postfix.
        """
        if string is not None and not isinstance(string, str):
            self.fail("First argument is not a string")
        if postfix and string is None:
            self.fail(self._formatMessage(
                msg, f"{string} does not end with '{postfix}'"
            ))
        if postfix and not string.endswith(postfix):
            self.fail(self._formatMessage(msg, "'{}' does not end with '{}'".format(
                ("[...]" if len(string) > len(postfix)+10 else string[:-len(postfix)-8])
                + string[-len(postfix)-8:],
                postfix
            )))

    def assertEqual(self, obj1: Any, obj2: Any, msg: Optional[str] = None):
        """
        Asserts that two objects are equal as determined by the '==' operator.
        In case one of the objects is a GIS point,
        asserts that it has the specified coordinates.
        """
        if isinstance(obj1, GeoPoint) or isinstance(obj2, GeoPoint):
            if isinstance(obj1, (tuple, list)):
                obj1 = GeoPoint(obj1, srid=SRID)
            if isinstance(obj2, (tuple, list)):
                obj2 = GeoPoint(obj2, srid=SRID)
            if obj1 != obj2:
                comparisson_message = "{} != {}".format(
                    getattr(obj1, 'wkt', str(obj1)),
                    getattr(obj2, 'wkt', str(obj2)),
                )
                self.fail(self._formatMessage(msg, comparisson_message))
        else:
            super().assertEqual(obj1, obj2, msg=msg)

    def assertLength(self, objects: Collection, value: int, msg: Optional[str] = None):
        """
        Asserts that an iterable has a specified number of items.
        """
        actual_length = len(objects)
        if actual_length != value:
            def truncate_repr(obj):
                string = " ".join(repr(obj).split())
                if len(string) > 52:
                    string = string[:50] + "[...]"
                return f"{obj.__class__.__qualname__} {string}"

            failure_message = (
                f"{actual_length} != {value}\n"
                + f"Object of type {objects.__class__.__qualname__} "
            )
            if actual_length > 0:
                failure_message += (
                    "has the following items:\n"
                    + ", ".join(truncate_repr(item) for item in objects)
                    + ("\n" if msg else "")
                )
            else:
                failure_message += "has no items"
            self.fail(self._formatMessage(msg, failure_message))

    class _AssertNotRaisesContext(_AssertRaisesContext):
        def __exit__(self, exc_type, exc_value, tb):
            if exc_type is not None:
                self.exception = exc_value.with_traceback(None)
                if not issubclass(exc_type, self.expected):
                    # Let unexpected exceptions pass through.
                    return False
                msg = self.test_case._formatMessage(self.msg, f"Unexpected {self.exception!r}")
                raise self.test_case.failureException(msg) from None
            else:
                traceback.clear_frames(tb)
                self.exception = None
            return True

    def assertNotRaises(self, expected_exception: type[Exception], *args, **kwargs):
        # Based on https://stackoverflow.com/a/49062929.
        context = self._AssertNotRaisesContext(expected_exception, self)
        try:
            return context.handle('assertNotRaises', args, kwargs)
        finally:
            context = None

    def assertCssClass(
            self,
            element: PyQuery | SoupResultSet | SoupTag | None,
            class_name: str,
            msg: Optional[str] = None,
    ):
        """
        Asserts that an HTML element (or at least one in a set of HTML elements)
        has the specified CSS class.
        Supports elements retrieved either via PyQuery or BeautifulSoup.
        """
        if isinstance(element, (PyQuery, SoupResultSet)) and len(element) == 0:
            element = None
        if isinstance(element, SoupTag):
            # Convert a single Tag into a ResultSet of 1 item for easier verification.
            element = SoupResultSet(None, [element])

        if isinstance(element, PyQuery):
            def full_id(el):
                element_id = f"#{el.get('id')}" if el.get("id") else ""
                return f"<{el.tag}{element_id}>"
            css_classes = {
                full_id(el):
                    el.get("class").split()
                    if el.get("class") is not None
                    else None
                for el in element
            }
            result = element.has_class(class_name)
        elif isinstance(element, SoupResultSet):
            def full_id(el):
                element_id = f"#{el.attrs['id']}" if el.attrs.get("id") else ""
                return f"<{el.name}{element_id}>"
            css_classes = {
                full_id(el): el.attrs.get("class")
                for el in element
            }
            result = any(class_name in (class_list or []) for class_list in css_classes)
        elif element is None:
            result = None
            self.fail(self._formatMessage(None, "Desired element is not in HTML."))
        else:
            result = None
            truncated_repr = safe_repr(element, short=True)
            self.fail(self._formatMessage(
                None,
                f"{type(element)} ({truncated_repr}) is not a parsed HTML element."
            ))

        if result is False:
            if all(class_list is None for class_list in css_classes.values()):
                element_repr = [full_id(el) for el in element]
                if len(element_repr) > 1:
                    failure_message = f"[{', '.join(element_repr)}] have no CSS classes"
                else:
                    failure_message = f"{element_repr[0]} has no CSS classes"
            else:
                failure_message = f"'{class_name}' not found in {css_classes}"
            self.fail(self._formatMessage(msg, failure_message))
