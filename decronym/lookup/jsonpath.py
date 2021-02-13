# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
import click
import json
import os

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
class LookupJsonPath(Lookup):
    def validate(self):
        self.valid = os.path.isfile(self.source) and self.source.endswith(".json")

    def find_direct(self, key: str) -> List[Result]:
        key = key.casefold()

        with click.open_file(self.source) as f:
            json_data = json.load(f)
        
        if key not in json_data:
            return []

        results = Result.schema().load(json_data[key], many=True)
        for r in results:
            r.source = self.source
        return results
        
    def to_dict(self) -> Dict:
        base = super().to_dict()
        print(base)
        base['path'] = self.source
        return base
