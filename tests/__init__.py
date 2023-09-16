from typing import TYPE_CHECKING, TypeVar

T = TypeVar('T')


def with_type_hint(baseclass: type[T]) -> type[T]:
    if TYPE_CHECKING:
        return baseclass
    else:
        return object
