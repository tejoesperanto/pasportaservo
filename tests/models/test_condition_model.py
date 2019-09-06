from django_webtest import WebTest

from ..factories import ConditionFactory


class ConditionModelTests(WebTest):
    def test_field_max_lengths(self):
        cond = ConditionFactory()
        self.assertEquals(cond._meta.get_field('name').max_length, 255)
        self.assertEquals(cond._meta.get_field('abbr').max_length, 20)

    def test_str(self):
        cond = ConditionFactory()
        self.assertEquals(str(cond), cond.name)
