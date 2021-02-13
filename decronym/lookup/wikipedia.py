# -*- coding: utf-8 -*-
from .base import Lookup
from .type import LookupType
from ..result import Result
from ..util import *
from ..config import Config
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
    def validate(self):
        self.valid = is_url_valid(self.source)
        
    def find_direct(self, key: str):
        key = key.casefold()
        r = requests.get(f"{self.source}{key.upper()}" )
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
                                source=self.source,
                                comment=comment,
                                tags=generate_tags(headline['id'].lower(), ["wiki"], mapping=self.config.get_tag_map()),
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
                                source=self.source,
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
                                    source=self.source,
                                    comment=sentence,
                                    tags=generate_tags(sentence, ["wiki"], mapping=self.config.get_tag_map())
                                )]
                        break
                else:
                    continue  # only executed if the inner loop did NOT break
                break  # only executed if the inner loop DID break
            
        return results