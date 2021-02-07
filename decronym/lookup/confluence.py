# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
from ..util import *
import requests
import getpass
from bs4 import BeautifulSoup
from collections import defaultdict

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

class LookupConfluenceTable(Lookup):
    def __init__(self, url:str, page_id:int,  type_: LookupType, enabled: bool = True):
        # Expects a confluence table in the followinng format:
        # |	ACRONYM | FULL | COMMENT
        request_url = f"{url}/rest/api/content/{page_id}?expand=body.storage"
        super().__init__(value=request_url,type_=type_,enabled=enabled)

    def validate(self):
        self.valid = is_url_valid(self.value)
        
    def load_direct(self):
        username = input("user: ")
        password = getpass.getpass("password: ")
        r = requests.get(self.value, auth=(username, password))
        if r.status_code != 200:
            # failed to fetch xml.
            return

        json_respnse = r.json()
        soup = BeautifulSoup(
            json_respnse["body"]["storage"]["value"].encode("UTF-8"), "html.parser"
        )
        source_text = f"{json_respnse['title']} at {self.value}"
        self.lut = defaultdict(List)
        for row in soup.find_all(lambda tag: tag.name == "tr"):
            cols = row.find_all(lambda tag: tag.name == "td")
            if len(cols) != 3:
                continue

            acronym = cols[0].text.strip()
            full = cols[1].text.strip()
            comment = cols[2].text.strip()

            if not is_acronym_valid(acronym):
                continue

            key = acronym.lower()
            if key not in self.lut:
                self.lut[key] = [
                    Result(
                        acronym,
                        full=full,
                        source=source_text,
                        comment=comment,
                        tags=["confluence"],
                    )
                ]
