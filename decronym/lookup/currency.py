# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
from ..util import *
import requests
import json
from bs4 import BeautifulSoup

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

class LookupCurrency(Lookup):
    def __init__(self, url, type_: LookupType, enabled: bool = True):
        super().__init__(value=url,type_=type_,enabled=enabled)

    def validate(self):
        self.valid = is_url_valid(self.value)

    def find_direct(self, 
                    key: str, 
                    update_cache:bool=False) -> List[Result]:

        r = requests.get(f"{self.value}")
        if r.status_code != 200:
            # failed to fetch xml.
            return

        soup = BeautifulSoup(r.text.encode("UTF-8"), "xml")

        results = []
        for tag in soup.find_all(lambda tag: tag.name == "CcyNtry" and tag.find("Ccy") and tag.find("Ccy").text.lower() == key):
            acronym = tag.find("Ccy")
            key = acronym.text.lower()
            full = tag.find("CcyNm")
            results.append( Result(
                        acronym.text,
                        full=full.text,
                        source=self.value,
                        tags=["currency","iso"]
                    ))

        return set(results)