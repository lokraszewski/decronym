from .result import Result

from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Sized,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    TYPE_CHECKING,
)


def filter(
    input: Optional[List], tags: Optional[List] = None
) -> Tuple[Optional[List], Optional[List]]:
    if tags:
        output = [r for r in input if not set(r.tags).isdisjoint(tags)]
        filtered = [r for r in input if set(r.tags).isdisjoint(tags)]
    else:
        output = input
        filtered = None

    return (output, filtered)