import traceback
from unittest.case import _AssertRaisesContext

from django.contrib.gis.geos import Point as GeoPoint

from maps import SRID


class AdditionalAsserts:
    def assertSurrounding(self, string, prefix=None, postfix=None, msg=None):
        """
        Asserts that the string has the given prefix and postfix.
        """
        self.assertStartsWith(string, prefix, msg)
        self.assertEndsWith(string, postfix, msg)

    def assertStartsWith(self, string, prefix=None, msg=None):
        """
        Asserts that the string has the given prefix.
        """
        if not isinstance(string, str):
            self.fail("First argument is not a string")
        if prefix and not string.startswith(prefix):
            self.fail(self._formatMessage(msg, "'{}' does not start with '{}'".format(
                string[:len(prefix)+8]
                + ("[...]" if len(string) > len(prefix)+10 else string[len(prefix)+10:]),
                prefix
            )))

    def assertEndsWith(self, string, postfix=None, msg=None):
        """
        Asserts that the string has the given postfix.
        """
        if not isinstance(string, str):
            self.fail("First argument is not a string")
        if postfix and not string.endswith(postfix):
            self.fail(self._formatMessage(msg, "'{}' does not end with '{}'".format(
                ("[...]" if len(string) > len(postfix)+10 else string[:-len(postfix)-8])
                + string[-len(postfix)-8:],
                postfix
            )))

    def assertEqual(self, obj1, obj2, msg=None):
        """
        Asserts that two GIS points are equal,
        or that a GIS point has the specified coordinates.
        """
        if isinstance(obj1, GeoPoint) or isinstance(obj2, GeoPoint):
            if isinstance(obj1, (tuple, list)):
                obj1 = GeoPoint(obj1, srid=SRID)
            if isinstance(obj2, (tuple, list)):
                obj2 = GeoPoint(obj2, srid=SRID)
            if not obj1 == obj2:
                comparisson_message = "{} != {}".format(
                    getattr(obj1, 'wkt', str(obj1)),
                    getattr(obj2, 'wkt', str(obj2)),
                )
                self.fail(self._formatMessage(msg, comparisson_message))
        else:
            super().assertEqual(obj1, obj2, msg=msg)

    def assertLength(self, objects, value, msg=None):
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

    def assertNotRaises(self, expected_exception, *args, **kwargs):
        # Based on https://stackoverflow.com/a/49062929.
        context = self._AssertNotRaisesContext(expected_exception, self)
        try:
            return context.handle('assertNotRaises', args, kwargs)
        finally:
            context = None
