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
    def validate(self):
        self.valid = is_url_valid(self.source)

    def find_direct(self, key: str) -> List[Result]:
        key = key.casefold()

        r = requests.get(f"{self.source}{key}")
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
                source=self.source,
                comment="",
                tags=["timezone"],
            )
        ]


