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
            )
        ]


class LookupSilmaril(LookupBase):
    def __init__(self, uri):
        self.uri = uri

    def keys(self):
        return []

    def __getitem__(self, key) -> List[Result]:
        root = etree.fromstring(requests.get(f"{self.uri}?{key}").text.encode("UTF-8"))

        return [
            Result(
                key,
                full=acro.findtext("expan", default=""),
                comment=acro.findtext("comment", default=""),
                source=self.uri,
            )
            for acro in root.findall(".//acro")
        ]


class LookupFactory:
    @classmethod
    def create(csl, type: LookupType, url=None, path=None, force=False):
        if type is LookupType.JSON:
            if not os.path.isfile(path):
                raise TypeError(
                    f"Invalid path ({path}) specified. Please check your config file. "
                )

            try:
                with click.open_file(path) as f:
                    json_data = json.load(f)
                    validate(schema=SOURCE_JSON_SCHEMA, instance=json_data)
            except ValueError as e:
                click.echo(f"JSON loaded from {path} is not valid")
                click.echo(e)
                return None
            except ValidationError as e:
                click.echo(
                    f"JSON loaded from {path} is not a valid definiton source file"
                )
                click.echo(e)
                return None

            return LookupFile(filepath=path, source=path)

        elif type is LookupType.JSON_REMOTE:
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
            return LookupFile(filepath=cache, source=url)

        elif type is LookupType.SILMARIL:
            if not is_url_valid(url):
                raise TypeError(
                    f"Invalid url ({url}) specified. Please check your config file. "
                )

            r = requests.head(url)
            if r.status_code != 200:
                click.echo(
                    f"URL ({url}) unreachable (code:{r.status_code}) - skipping."
                )
                return None
            return LookupSilmaril(uri=url)
        elif type is LookupType.TIMEDATE:
            if not is_url_valid(url):
                raise TypeError(
                    f"Invalid url ({url}) specified. Please check your config file. "
                )
            r = requests.head(url)
            if r.status_code != 200:
                click.echo(
                    f"URL ({url}) unreachable (code:{r.status_code}) - skipping."
                )
                return None
            return LookupTimeAndDate(url=url)
        else:
            print(f"Unknown type {type} ")
        return None

    @classmethod
    def from_config(cls, config: Config, force=False):
        sources = []
        for url in config.get_urls():
            new = LookupFactory.create(LookupType.JSON_REMOTE, url=url, force=force)
            if new:
                sources.append(new)

        for path in config.get_paths():
            if os.path.isfile(path):
                new = LookupFactory.create(LookupType.JSON, path=path)
                print(new)

            elif os.path.isdir(path):
                for dirpath, _, files in os.walk(os.path.abspath(path)):
                    for file in files:
                        if file.endswith(".json"):
                            new = LookupFactory.create(
                                LookupType.JSON, path=os.path.join(dirpath, file)
                            )
                            print(new)

        silmaril_config = config.get_third_party("silmaril")
        if silmaril_config and silmaril_config["enable"]:
            new = LookupFactory.create(LookupType.SILMARIL, url=silmaril_config["uri"])
            if new:
                sources.append(new)

        timedate_config = config.get_third_party("timeanddate")
        if timedate_config and timedate_config["enable"]:
            new = LookupFactory.create(LookupType.TIMEDATE, url=timedate_config["url"])
            if new:
                sources.append(new)

        return sources if sources else None


class LookupCollector(object):
    """The mega lookup. Takes in a list of Lookup objects for easy searching"""

    def __init__(self, config: Config = None, luts: Optional[List] = None):
        self.sources = LookupFactory.from_config(config)

    def keys(self) -> Optional[list]:
        return [src.keys() for src in self.sources]

    def find(self, acronym: str) -> Optional[list]:
        matches = []
        for lut in self.sources:
            temp = lut[acronym]
            if temp:
                matches = matches + temp

        return matches if len(matches) > 0 else None

    def find_similar(self, acronym: str) -> Optional[list]:
        suggested = []
        for lut in self.sources:
            temp = difflib.get_close_matches(acronym, lut.keys())
            suggested = suggested + temp
        return suggested if len(suggested) > 0 else None

    def __getitem__(self, key) -> Optional[List[Result]]:
        return self.find(key)

    def get_luts(self):
        return self.sources