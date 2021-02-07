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

class LookupJsonDir(Lookup):
    def __init__(self, path, type_: LookupType, enabled: bool = True):
        super().__init__(value=path,type_=type_,enabled=enabled)


    def validate(self):
        self.valid = os.path.isdir(self.value)

    def find_direct(self, key: str) -> List[Result]:
        key = key.casefold()
        results = []
        for dir, _, files in os.walk(os.path.abspath(self.value)):
            for file in files:
                if not file.endswith('.json'):
                    continue

                fullpath = os.path.join(dir, file)
                
                with click.open_file(fullpath) as f:
                    json_data = json.load(f)
                    # TODO: add validation to check if contents will work

                if key in json_data:
                    temp_results = Result.schema().load(json_data[key], many=True)
                    for r in temp_results:
                        r.source = fullpath
                    results += temp_results
        
        return set(results)


    def to_dict(self) -> Dict:
        base = super().to_dict()
        print(base)
        base['path'] = self.value
        return base