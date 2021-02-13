# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
from ..util import *
import requests
import json

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

class LookupRemote(Lookup):
    def validate(self):
        self.valid = is_url_valid(self.source)
        
    def find_direct(self, key: str) -> List[Result]:
        try:
            r = requests.get(self.source)
            if r.status_code != 200:
                out_warn(
                    f"URL ({self.source}) unreachable (code:{r.status_code}) - skipping."
                )
                return []

            results = []
            json_data = json.loads(r.text)
            for entry, items in json_data.items():
                if entry.casefold() != key.casefold():
                    continue
                results += Result.schema().load(items, many=True)

            for r in results:
                r.source = self.source
            return results

        except Exception as e:
            out_warn(f"Failed to get json from URL ({self.source}) {e}")
            return []

