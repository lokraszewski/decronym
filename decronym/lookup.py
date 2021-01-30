# -*- coding: utf-8 -*-
import os
import requests
import json
import click
import re
import difflib

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
from .config import Config
from .util import is_url_valid, generate_cache_filepath


SOURCE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
        "defs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "acro": {"type": "string"},
                    "full": {"type": "string"},
                    "comment": {"type": "string"},
                    "suggested": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["acro", "full"],
            },
        },
    },
    "required": ["defs"],
}


class LookupType(Enum):
    JSON = auto()
    JSON_REMOTE = auto()
    SILMARIL = auto()
    TIMEDATE = auto()
    ISO_CURRENCY = auto()


class LookupBase(object):
    def load(self, force=False) -> None:
        pass

    def update_cache(self) -> None:
        pass

    def drop(self):
        pass

    def __getitem__(self, key) -> List[Result]:
        return []


class LookupFile(LookupBase):
    def __init__(self, filepath, json_data=None, source=None):
        self.filepath = filepath
        self.lut = None
        self.source = source if source else filepath

    def load(self, force=False) -> None:
        if not self.lut or force:
            self.lut = defaultdict(list)
            with click.open_file(self.filepath) as f:
                json_raw = json.load(f)

                for item in json_raw["defs"]:
                    self.lut[item["acro"].lower()].append(
                        Result.fromJSON(item, meta=json_raw["meta"], source=self.source)
                    )

    def drop(self):
        self.lut = None

    def keys(self):
        return self.lut.keys()

    def __getitem__(self, key) -> List[Result]:
        if self.lut is None:
            self.load()
        return self.lut.get(key, [])


class LookupTimeAndDate(LookupBase):
    def __init__(self, url):
        self.url = url

    def keys(self):
        return []

    def __getitem__(self, key) -> List[Result]:
        r = requests.get(f"{self.url}{key}")
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
        else:
            comment = None

        acronym = soup.find(id="bct")
        return [
            Result(
                key,
                full=acronym.contents[-1].lstrip(),
                source=self.url,
                comment=comment,
                tags=["timezone"],
            )
        ]


class LookupCurrency(LookupBase):
    def __init__(self, url):
        self.url = url

    def keys(self):
        return []

    def __getitem__(self, key) -> List[Result]:
        r = requests.get(f"{self.url}")
        if r.status_code != 200:
            return []

        html_text = r.text.encode("UTF-8")
        soup = BeautifulSoup(html_text, "xml")

        matches = soup.find_all(
            lambda tag: tag.name == "CcyNtry"
            and tag.find("Ccy")
            and tag.find("Ccy").text == key.upper()
        )

        names = set([tag.find("CcyNm").text for tag in matches if tag.find("CcyNm")])

        return [
            Result(key.upper(), full=name, source=self.url, tags=["iso", "currency"])
            for name in names
        ]


class LookupFactory:
    @classmethod
    def create_json(cls, path, force=False, source=None):
        if not os.path.isfile(path):
            raise TypeError(
                f"Invalid path ({path}) specified. Please check your config file. "
            )

        if source is None:
            source = path

        try:
            with click.open_file(path) as f:
                json_data = json.load(f)
                validate(schema=SOURCE_JSON_SCHEMA, instance=json_data)
        except ValueError as e:
            click.echo(f"JSON loaded from {path} is not valid")
            click.echo(e)
            return None
        except ValidationError as e:
            click.echo(f"JSON loaded from {path} is not a valid definiton source file")
            click.echo(e)
            return None

        return LookupFile(filepath=path, source=source)

    @classmethod
    def create_json_remote(cls, url, force=False):
        # First check if it is a valid url:
        if not is_url_valid(url):
            raise TypeError(
                f"Invalid url ({url}) specified. Please check your config file. "
            )

        cache = generate_cache_filepath(url)
        if not os.path.isfile(cache) or force:
            # Check if address is reachable.
            r = requests.head(url)
            if r.status_code != 200:
                click.echo(
                    f"URL ({url}) unreachable (code:{r.status_code}) - skipping."
                )
                return None

            try:
                raw = requests.get(url).text
                json_data = json.loads(raw)
                validate(schema=SOURCE_JSON_SCHEMA, instance=json_data)
            except ValueError as e:
                click.echo(f"JSON fetched from {url} is not valid")
                click.echo(e)
                return None
            except ValidationError as e:
                click.echo(
                    f"JSON fetched from {url} is not a valid definiton source file"
                )
                click.echo(e)
                return None

            # Ensure the directory exists
            directory = os.path.dirname(cache)
            if not os.path.exists(directory):
                os.makedirs(directory)
            with click.open_file(cache, mode="w+") as f:
                f.write(json.dumps(json_data))

        # Data downloaded and valid
        return cls.create_json(path=cache, source=url)

    @classmethod
    def create_time_date(cls, url, force=False):
        if not is_url_valid(url):
            raise TypeError(
                f"Invalid url ({url}) specified. Please check your config file. "
            )
        r = requests.head(url)
        if r.status_code != 200:
            click.echo(f"URL ({url}) unreachable (code:{r.status_code}) - skipping.")
            return None
        return LookupTimeAndDate(url=url)

    @classmethod
    def create_iso_currency(cls, url, force=False):
        if not is_url_valid(url):
            raise TypeError(
                f"Invalid url ({url}) specified. Please check your config file. "
            )
        r = requests.head(url)
        if r.status_code != 200:
            click.echo(f"URL ({url}) unreachable (code:{r.status_code}) - skipping.")
            return None
        return LookupCurrency(url=url)

    @classmethod
    def create(cls, type: LookupType, url=None, path=None, force=False):
        if type is LookupType.JSON:
            return cls.create_json(path=path, force=force)

        elif type is LookupType.JSON_REMOTE:
            return cls.create_json_remote(url=url, force=force)

        elif type is LookupType.TIMEDATE:
            return cls.create_time_date(url=url, force=force)

        elif type is LookupType.ISO_CURRENCY:
            return cls.create_iso_currency(url=url)
        else:
            print(f"Unknown type {type} ")
            return None

    @classmethod
    def name_to_type(cls, name: str) -> LookupType:
        match = {
            "path": LookupType.JSON,
            "url": LookupType.JSON_REMOTE,
            "timeanddate": LookupType.TIMEDATE,
            "iso_currency": LookupType.ISO_CURRENCY,
        }
        return match[name]

    @classmethod
    def from_config(cls, config: Config, force=False):
        sources = []
        for name, details in config.get_sources():
            type = cls.name_to_type(name)
            if type == LookupType.JSON_REMOTE:
                for url in details:
                    sources.append(LookupFactory.create(type, url=url))

            elif type == LookupType.JSON:
                for path in details:
                    if os.path.isfile(path):
                        sources.append(LookupFactory.create(type, path=path))
                    elif os.path.isdir(path):
                        for dirpath, _, files in os.walk(os.path.abspath(path)):
                            for file in files:
                                if file.endswith(".json"):
                                    sources.append(
                                        LookupFactory.create(
                                            type, path=os.path.join(dirpath, file)
                                        )
                                    )

            elif details["enable"]:
                sources.append(LookupFactory.create(type, url=details["url"]))

        return [src for src in sources if src] if sources else None


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
            temp = difflib.get_close_matches(acronym, lut.keys())
            suggested = suggested + temp
        return suggested if len(suggested) > 0 else None

    def __getitem__(self, key) -> Optional[List[Result]]:
        return self.find(key)

    def get_luts(self):
        return self.sources