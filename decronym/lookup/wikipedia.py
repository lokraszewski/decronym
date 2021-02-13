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

class LookupWikipedia(Lookup):
    def __init__(self, url:str,   type_: LookupType, enabled: bool = True):
        super().__init__(value=url,type_=type_,enabled=enabled)

    def validate(self):
        self.valid = is_url_valid(self.value)
        
    def find_direct(self, key: str):
        key = key.casefold()
        r = requests.get(f"{self.value}{key.upper()}" )
        if r.status_code != 200:
            return []

        
        soup = BeautifulSoup(
            r.text, "html.parser"
        )

        results = []

        # This is a super naive approach for the proof of concept. 
        for t in soup.find_all("p"):
            if "may refer to" in t.text and key.upper() in t.text:
                # Disambiguation
                for headline in soup.find_all("span", {"class": "mw-headline"}):
                    if "see also" in headline.text.casefold():
                        # Skip the disambiguation and similar matches
                        continue
                    
                    for item in headline.parent.findNext('ul').find_all("li"):
                        a = item.find("a")
                        if a and a.has_attr('title'):
                            full = a['title']
                        else:
                            continue
                        comment = item.text
                        results += [Result(
                                acronym = key,
                                full=full,
                                source=self.value,
                                comment=comment,
                                tags=generate_tags(headline['id'].lower(), ["wiki"]),
                            )]

                else:
                    # Has no headlines
                    for item in t.parent.findNext("ul").find_all("li"):
                        a = item.find("a")
                        if a and a.has_attr('title'):
                            full = a['title']
                        else:
                            continue

                        tags=["wiki"]
                        comment = item.text
                        results += [Result(
                                acronym = key,
                                full=full,
                                source=self.value,
                                comment=comment,
                                tags=tags
                            )]
                break
        else:
            for t in soup.find_all("p"):
                for sentence in [sentence for sentence in t.text.split('.') if f"({key.upper()}" in sentence]:
                    for full, _ in find_acronym_groups(sentence, key):
                        results += [Result(
                                    acronym = key,
                                    full=full.strip(),
                                    source=self.value,
                                    comment=sentence,
                                    tags=generate_tags(sentence, ["wiki"])
                                )]
                        break
                else:
                    continue  # only executed if the inner loop did NOT break
                break  # only executed if the inner loop DID break
            
        return results