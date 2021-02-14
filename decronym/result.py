# -*- coding: utf-8 -*-
import hashlib
import os
from jsonschema import validate, ValidationError
from dataclasses import dataclass, field
import dataclasses, json
from dataclasses_json import dataclass_json
import click
from lxml import etree
import textwrap
from typing import (
    Any,
    Callable,
    Collection,
    DefaultDict,
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

CACHE_JSON_SCHEMA = {
    "definitions": {
        "acronym": {
            "type": "object",
            "properties": {
                "acronym": {"type": "string"},
                "comment": {"type": "string"},
                "source": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "full": {"type": "string"},
            },
            "required": ["acronym", "full"],
        }
    },
    "patternProperties": {
        "^[a-zA-Z0-9\-]+$": {
            "type": "array",
            "items": {"$ref": "#/definitions/acronym"},
        }
    },
}


@dataclass_json
@dataclass(unsafe_hash=True)
class Result(object):
    acronym: str
    full: str
    comment: str = ""
    source: str = field(default_factory=str, compare=False)
    tags: List[str] = field(default_factory=list, compare=False)

    def pretty(self):
        out = "\t"
        for letter in self.full:
            if letter.isupper():
                out += click.style(letter, bold=True, fg="green")
            else:
                out += click.style(letter, bold=True)
        out += "\n"

        if self.comment:
            lines = textwrap.wrap(self.comment)
            for line in lines:
                out += click.style(f"\t{line}\n", fg="white")

        if self.tags:
            tags_formatted = " ".join([f"[{tag}]" for tag in self.tags])
            out += click.style(f"\t{tags_formatted}\n", fg="green")

        if self.source:
            out += click.style(f"\tfrom: {self.source}\n", fg="blue")

        return out


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class ResultCache:
    """Caches results and saves/loads to a file."""

    def __init__(self, path: str = ""):
        self.cache_: Dict[str, Result] = DefaultDict(list)
        self.path = path
        self.md5 = None
        self.load()

    def __del__(self):
        self.save()

    def load(self, path=None):
        if not path:
            path = self.path

        if os.path.isfile(path) and path.endswith(".json"):
            with click.open_file(path) as f:
                # json_data = json.load(f)
                raw = f.read()
                dhash = hashlib.md5()
                dhash.update(raw.encode())

                try:
                    json_data = json.loads(raw)
                    validate(instance=json_data, schema=CACHE_JSON_SCHEMA)
                except ValidationError as e:
                    print(e)
                    return 

                self.md5 = dhash.digest()
                for key, items in json_data.items():
                    self.cache_[key.casefold()] = Result.schema().load(items, many=True)

    def save(self, path=None):
        """ Writes Lookup data to cache file """
        if not path:
            path = self.path

        encoded = json.dumps(
            self.cache_, cls=EnhancedJSONEncoder, sort_keys=True
        ).encode()
        dhash = hashlib.md5()
        dhash.update(encoded)

        if self.md5 == dhash.digest():
            # hash unchanged, skip
            return

        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with click.open_file(path, mode="bw+") as f:
            f.write(encoded)

    def add(self, items):
        for item in items:
            key = item.acronym.casefold()
            if item not in self.cache_[key]:
                self.cache_[key].append(item)

    def __iter__(self):
        """ Returns the Iterator object """
        return iter(self.cache_)

    def __getitem__(self, key):
        return self.cache_[key]

    def keys(self):
        return self.cache_.keys()

    @classmethod
    def from_file(cls, path):
        return cls(path=path)