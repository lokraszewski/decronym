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
    def __init__(self, url,  type_: LookupType, enabled: bool = True):
        super().__init__(value=url,type_=type_,enabled=enabled)
        
    def validate(self):
        self.valid = is_url_valid(self.value)
        
    def find_direct(self, key: str) -> List[Result]:
        try:
            r = requests.get(self.value)
            if r.status_code != 200:
                out_warn(
                    f"URL ({self.value}) unreachable (code:{r.status_code}) - skipping."
                )
                return []

            json_data = json.loads(r.text)
            results = [Result.from_dict(raw) for raw in list(filter(lambda x:x["acro"].casefold()== key, json_data['defs']))]
            return set(results)

        except Exception as e:
            out_warn(f"Failed to access URL ({self.value}) {e}")
            return []

