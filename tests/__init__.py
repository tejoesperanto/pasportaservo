import typing
from typing import TYPE_CHECKING


def with_type_hint[T](baseclass: type[T]) -> type[T]:
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


class UserTag(tuple[str, ...]):
    """
    Immutable sequence of tags for a :class:`~hosting.models.PasportaServoUser`
    or :class:`~hosting.models.Profile` object.
    """

    def __new__(cls, *args: str):
        return super().__new__(cls, args)

    def __str__(self):
        return ';'.join(self)

    __repr__ = __str__

    @typing.overload
    def matches_any(self, *tags: str) -> bool:
        ...

    @typing.overload
    def matches_any(self, tags: typing.Iterable[str], /) -> bool:
        ...

    def matches_any(self, *args) -> bool:
        return self._check_correlation(args, any)

    @typing.overload
    def matches_all(self, *tags: str) -> bool:
        ...

    @typing.overload
    def matches_all(self, tags: typing.Iterable[str], /) -> bool:
        ...

    def matches_all(self, *args) -> bool:
        return self._check_correlation(args, all)

    @typing.overload
    def matches_none(self, *tags: str) -> bool:
        ...

    @typing.overload
    def matches_none(self, tags: typing.Iterable[str], /) -> bool:
        ...

    def matches_none(self, *args):
        return not self._check_correlation(args, any)

    def _check_correlation(
            self,
            tags: typing.Sequence[str | typing.Iterable[str]],
            quantifier: typing.Callable[[typing.Iterable[bool]], bool],
    ) -> bool:
        if len(tags) == 1 and not isinstance(tags[0], str):
            target_tags = set(tags[0])
        else:
            target_tags = set(tags)

        return quantifier(tag in self for tag in target_tags)
