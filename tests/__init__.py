from typing import TYPE_CHECKING, TypeVar

T = TypeVar('T')


def with_type_hint(baseclass: type[T]) -> type[T]:
    if TYPE_CHECKING:
        return baseclass
    else:
        return object


if TYPE_CHECKING:
    from django.http import HttpResponse

    from webtest import TestResponse, forms

    class DjangoWebtestResponse(TestResponse, HttpResponse):

        forms: dict[int | str, forms.Form]
        """
        A dictionary containing all the forms in the page as :class:`~webtest.forms.Form`
        objects. Indexes are both numerical and by form id (if the form was given an id).
        """

else:
    from django_webtest import (
        DjangoWebtestResponse as OriginalDjangoWebtestResponse,
    )

    DjangoWebtestResponse = OriginalDjangoWebtestResponse
