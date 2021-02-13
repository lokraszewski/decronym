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
                                tags=["wiki", headline['id'].lower()],
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
                    words = re.split('\W+', sentence)
                    current_letter = 0
                    full_ar = []
                    for word in words:
                        if word.casefold()[0] == key[current_letter]:
                            full_ar.append(word)
                            current_letter+=1
                            if current_letter == len(key):
                                break
                        else:
                            full_ar = []
                            current_letter = 0

                    if len(full_ar) != len(key):
                        break
                    
                    results += [Result(
                                acronym = key,
                                full=" ".join(full_ar),
                                source=self.value,
                                comment=sentence,
                                tags=["wiki"]
                            )]
                    break
            
        return results