# -*- coding: utf-8 -*-
import os
import requests
import json
import click
import re
import difflib
import getpass

from bs4 import BeautifulSoup
from jsonschema import validate, ValidationError
from collections import defaultdict
from lxml import etree
from enum import Enum, auto
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

from .result import Result
from .config import Config, SourceType
from .util import *


class CachedLookup(object):
    def __init__(self, path):
        self.path = path
        self.cache_path = generate_cache_filepath(path)
        self.lut = None
        self.meta = {"source": path}
        self.cache_changed = False
        self.valid = True

    def __del__(self):
        if self.cache_changed:
            self.write_to_cache()

    def load_from_source(self):
        try:
            self.lut = defaultdict(list)
            for result in Result.load_all_from_file(path=self.path):
                self.lut[result.acro.lower()].append(result)
            self.cache_changed = True
        except json.decoder.JSONDecodeError as e:
            out_warn(f"Failed to load from {self.path}, invalid json format")
            self.valid = False
        except ValidationError as e:
            out_warn(
                f"Failed to load from {self.path}, contents do not pass validation."
            )
            self.valid = False

    def load_from_cache(self):
        if not os.path.isfile(self.cache_path):
            return

        self.lut = defaultdict(list)

        try:
            for result in Result.load_all_from_file(path=self.cache_path):
                self.lut[result.acro.lower()].append(result)
        except Exception as e:
            out_warn(f"failed to load from cache {e}")
            self.drop()

    def load(self, force=False) -> None:
        """ Loads data from either cache or source. """
        # Attempt to load from cache first:
        if not force:
            self.load_from_cache()

        # Data was not loaded successfully from cache.
        if self.lut is None:
            self.load_from_source()

    def write_to_cache(self) -> None:
        """ Writes Lookup data to cache file """
        if self.lut is None:
            self.load()

        if self.lut is None:
            return

        flattened = [item for sublist in self.lut.values() for item in sublist]
        Result.save_to_json(path=self.cache_path, items=flattened, meta=self.meta)

    def drop(self):
        """ Drops lookup table. """
        self.lut = None

    def keys(self):
        return self.lut.keys() if self.lut else []

    def is_loaded(self) -> bool:
        return bool(self.lut is not None)

    def is_valid(self) -> bool:
        return self.valid

    def __getitem__(self, key) -> List[Result]:
        if not self.is_loaded():
            self.load()

        if not self.is_valid():
            return []

        return self.lut.get(key.lower(), [])


class LookupRemote(CachedLookup):
    def __init__(self, url):
        self.url = url
        self.cache_path = generate_cache_filepath(url)
        self.lut = None
        self.meta = {"source": url}
        self.cache_changed = False
        self.valid = True

    def load_from_source(self):
        if not is_url_valid(self.url):
            raise TypeError(
                f"Invalid url ({self.url}) specified. Please check your config file. "
            )

        try:
            r = requests.get(self.url)
            if r.status_code != 200:
                out_warn(
                    f"URL ({self.url}) unreachable (code:{r.status_code}) - skipping."
                )
            self.lut = defaultdict(list)
            for result in Result.load_all_from_json_str(r.text):
                self.lut[result.acro.lower()].append(result)
            self.cache_changed = True
        except:
            out_warn(f"URL ({self.url}) unreachable (code:{r.status_code}) - skipping.")
            self.valid = False


class LookupTimeAndDate(CachedLookup):
    def __init__(self, url):
        self.url = url
        self.cache_path = generate_cache_filepath(url)
        self.lut = None
        self.meta = {"source": url}
        self.cache_changed = False
        self.valid = True

    def load_from_source(self):
        # not supported
        pass

    def __getitem__(self, key) -> List[Result]:
        if self.lut is None:
            self.load()

        # Check if item is in lut
        if self.lut is not None:
            if key in self.lut:
                return self.lut[key]

        r = requests.get(f"{self.url}{key.lower()}")
        if r.status_code != 200:
            return []

        html_text = r.text.encode("UTF-8")
        soup = BeautifulSoup(html_text, "html.parser")

        if soup.find(text="Unknown timezone abbreviation"):
            return []

        hrmn = soup.find(id="hourmin0")
        sec = soup.find(id="sec0")
        if hrmn and sec:
            comment = f"Time now: {hrmn.text}:{sec.text}"
        elif hrmn:
            comment = f"Time now: {hrmn.text}"
        else:
            comment = None

        acronym = soup.find(id="bct")
        if self.lut is None:
            self.lut = defaultdict(list)

        self.lut[key.lower()] = [
            Result(
                key,
                full=acronym.contents[-1].lstrip(),
                source=self.url,
                comment=comment,
                tags=["timezone"],
            )
        ]
        self.cache_changed = True
        return self.lut[key]


class LookupCurrency(CachedLookup):
    def __init__(self, url):
        self.url = url
        self.cache_path = generate_cache_filepath(url)
        self.lut = None
        self.meta = {"source": url}
        self.cache_changed = False
        self.valid = True

    def load_from_source(self):
        r = requests.get(f"{self.url}")
        if r.status_code != 200:
            # failed to fetch xml.
            return

        soup = BeautifulSoup(r.text.encode("UTF-8"), "xml")

        self.lut = defaultdict(List)
        for tag in soup.find_all(lambda tag: tag.name == "CcyNtry" and tag.find("Ccy")):
            acronym = tag.find("Ccy")
            key = acronym.text.lower()
            full = tag.find("CcyNm")
            if key not in self.lut:
                self.lut[key] = [
                    Result(
                        acronym.text,
                        full=full.text,
                        source=self.url,
                        tags=["iso", "currency"],
                    )
                ]

        self.cache_changed = True


class LookupConfluenceTable(CachedLookup):
    def __init__(self, url, page_id=""):
        # Expects a confluence table in the followinng format:
        # |	ACRONYM | FULL | COMMENT
        self.url = url
        self.page_id = page_id
        self.cache_path = generate_cache_filepath(url)
        self.lut = None
        self.meta = {"source": url}
        self.cache_changed = False
        self.valid = True

    def load_from_source(self):
        print(f"\n{self.url} requires credentials.")
        username = input("user: ")
        password = getpass.getpass("password: ")
        api_url = "/rest/api/content"
        request_url = f"{self.url}/{api_url}/{self.page_id}?expand=body.storage"

        r = requests.get(request_url, auth=(username, password))
        if r.status_code != 200:
            # failed to fetch xml.
            return

        json_respnse = r.json()
        soup = BeautifulSoup(
            json_respnse["body"]["storage"]["value"].encode("UTF-8"), "html.parser"
        )
        source_text = f"{json_respnse['title']} at {self.url}"
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
                self.cache_changed = True


class LookupFactory:
    @classmethod
    def create(cls, source: Dict):
        type_ = SourceType.from_str(source["type"])
        if type_ is SourceType.JSON_PATH:
            return CachedLookup(path=source["path"])
        elif type_ is SourceType.JSON_URL:
            return LookupRemote(url=source["url"])
        elif type_ is SourceType.TIMEDATE:
            return LookupTimeAndDate(url=source["url"])
        elif type_ is SourceType.ISO_CURRENCY:
            return LookupCurrency(url=source["url"])
        elif type_ is SourceType.CONFLUENCE_TABLE:
            return LookupConfluenceTable(
                url=source["url"], page_id=source["page_id"]
            )
        else:
            out_err(f"Unknown type {type} ")
            return None

    @classmethod
    def from_config(cls, config: Config):
        sources = []
        for source in config.get_enabled_sources():
            type_ = SourceType.from_str(source["type"])
            if type_ == SourceType.JSON_PATH:
                path = source["path"]
                if os.path.isfile(path) and path.endswith(".json"):
                    sources.append(LookupFactory.create(source))
                elif os.path.isdir(path):
                    for dirpath, _, files in os.walk(os.path.abspath(path)):
                        for file in files:
                            if file.endswith(".json"):
                                temp_src = source
                                temp_src["path"] = os.path.join(dirpath, file)
                                sources.append(LookupFactory.create(temp_src))
            else:
                sources.append(LookupFactory.create(source))

        return sources


class LookupCollector(object):
    """The mega lookup. Takes in a list of Lookup objects for easy searching"""

    def __init__(self, config: Config = None, luts: Optional[List] = None):
        self.sources = LookupFactory.from_config(config)

    def keys(self) -> Optional[list]:
        return [src.keys() for src in self.sources]

    def find(self, acronym: str) -> Optional[list]:
        if not self.sources:
            return None

        matches = []
        for lut in self.sources:
            temp = lut[acronym]
            if temp:
                matches = matches + temp

        return matches if len(matches) > 0 else None

    def find_similar(self, acronym: str) -> Optional[list]:
        if not self.sources:
            return None

        suggested = []
        for lut in self.sources:
            temp = difflib.get_close_matches(acronym.lower(), lut.keys())
            suggested = suggested + temp
        return suggested if len(suggested) > 0 else None

    def __getitem__(self, key) -> Optional[List[Result]]:
        return self.find(key)

    def get_luts(self):
        return self.sources
