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
