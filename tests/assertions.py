
class AdditionalAsserts:
    def assertSurrounding(self, string, prefix, postfix, msg=None):
        """
        Asserts that the string has the given prefix and postfix.
        """
        if not isinstance(string, str):
            self.fail("First argument is not a string")
        if not string.startswith(prefix):
            self.fail(self._formatMessage(msg, "'{}' does not start with '{}'".format(
                string[:len(prefix)+8]
                + ("[...]" if len(string) > len(prefix)+10 else string[len(prefix)+10:]),
                prefix
            )))
        if not string.endswith(postfix):
            self.fail(self._formatMessage(msg, "'{}' does not end with '{}'".format(
                ("[...]" if len(string) > len(postfix)+10 else string[:-len(postfix)-8])
                + string[-len(postfix)-8:],
                postfix
            )))
