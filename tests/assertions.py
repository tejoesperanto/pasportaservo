
class AdditionalAsserts:
    def assertSurrounding(self, string, prefix=None, postfix=None, msg=None):
        """
        Asserts that the string has the given prefix and postfix.
        """
        if not isinstance(string, str):
            self.fail("First argument is not a string")
        if prefix and not string.startswith(prefix):
            self.fail(self._formatMessage(msg, "'{}' does not start with '{}'".format(
                string[:len(prefix)+8]
                + ("[...]" if len(string) > len(prefix)+10 else string[len(prefix)+10:]),
                prefix
            )))
        if postfix and not string.endswith(postfix):
            self.fail(self._formatMessage(msg, "'{}' does not end with '{}'".format(
                ("[...]" if len(string) > len(postfix)+10 else string[:-len(postfix)-8])
                + string[-len(postfix)-8:],
                postfix
            )))
