from typing import TYPE_CHECKING, TypeVar

T = TypeVar('T')


def with_type_hint(baseclass: type[T]) -> type[T]:
    if TYPE_CHECKING:
        return baseclass
    else:
        return object


if TYPE_CHECKING:
    from django.http import HttpResponse

    from webtest import TestResponse

    class DjangoWebtestResponse(TestResponse, HttpResponse):
        pass
else:
    from django_webtest import (
        DjangoWebtestResponse as OriginalDjangoWebtestResponse,
    )

    DjangoWebtestResponse = OriginalDjangoWebtestResponse
