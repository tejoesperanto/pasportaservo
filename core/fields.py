from typing import TYPE_CHECKING, Any, Self, overload

from django.db import models

from simplemde.fields import SimpleMDEField as ThirdPartySimpleMDEField

if TYPE_CHECKING:
    class SimpleAnnotationFieldMixin[ValueT]:
        def __new__(cls, *args, **kwargs) -> Self:
            ...

        # Class access
        @overload
        def __get__(self, instance: None, owner: Any) -> Self:  # type: ignore[overload]
            ...

        # Model instance access
        @overload
        def __get__(self, instance: models.Model, owner: Any) -> ValueT:
            ...

        # Non-Model instance access
        @overload
        def __get__(self, instance: Any, owner: Any) -> Self:
            ...
else:
    class SimpleAnnotationFieldMixin[UnusedT]:
        pass


class SimpleMDEField(SimpleAnnotationFieldMixin[str], ThirdPartySimpleMDEField):
    pass
