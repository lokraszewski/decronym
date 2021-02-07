# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
from ..util import *
import requests
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

class LookupTimeAndDate(Lookup):
    def __init__(self, url, type_: LookupType, enabled: bool = True):
        super().__init__(value=url,type_=type_,enabled=enabled)

    def validate(self):
        self.valid = is_url_valid(self.value)

    def find_direct(self, key: str) -> List[Result]:
        key = key.casefold()

        r = requests.get(f"{self.value}{key}")
        if r.status_code != 200:
            return []

        html_text = r.text.encode("UTF-8")
        soup = BeautifulSoup(html_text, "html.parser")

        if soup.find(text="Unknown timezone abbreviation"):
            return []

        acronym = soup.find(id="bct")

        return [
            Result(
                acronym=key,
                full=acronym.contents[-1].lstrip(),
                source=self.value,
                comment="",
                tags=["timezone"],
            )
        ]


