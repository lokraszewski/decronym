# -*- coding: utf-8 -*-
import os
import click
import json
import hashlib

from jsonschema import validate, ValidationError
from pkg_resources import resource_filename
from enum import Enum, auto
from .util import *
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


JSON_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "bool"},
                    "type": {"type": "string"},
                    "path": {"type": "string"},
                    "url": {"type": "string"},
                    "needs_auth": {"type": "bool"},
                    "username": {"type": "string"},
                },
            },
        }
    },
}


def select_config_file(path: str = None) -> str:
    """Find a valid config path.

    Will attempt to priorities paths in the following order:
    - path given from the user
    - user config path stored in home dir
    - package default config file shipped

    Args:
        path (str): Path given by the user.

    Returns:
        str: Path to config file to be used.
    """
    user = os.path.join(os.environ["HOME"], ".config/decronym", "config.json")
    package_default = os.path.abspath(resource_filename("decronym", "config.json"))

    for candidate in (path, user, package_default):
        if not candidate:
            continue
        if os.path.isfile(candidate) and candidate.endswith(".json"):
            return candidate
    else:
        return None


class SourceType(Enum):
    JSON_PATH = auto()
    JSON_URL = auto()
    TIMEDATE = auto()
    ISO_CURRENCY = auto()
    CONFLUENCE_TABLE = auto()

    @classmethod
    def from_str(cls, label):
        if label in ("path", "JSON_PATH"):
            return cls.JSON_PATH
        elif label in ("url", "JSON_URL"):
            return cls.JSON_URL
        elif label in ("timeanddate", "TIMEDATE"):
            return cls.TIMEDATE
        elif label in ("iso_currency", "ISO_CURRENCY"):
            return cls.ISO_CURRENCY
        elif label in ("confluence_table", "CONFLUENCE_TABLE"):
            return cls.CONFLUENCE_TABLE
        else:
            raise NotImplementedError


class Config(object):
    """Stores configuration"""

    def __init__(self, path=None) -> None:
        self.config = None
        self.hash = None
        self.config_changed = False
        self.path = select_config_file(path)

        # Check if any valid path has beeen given.
        if not self.path:
            raise click.UsageError(f"No valid config found. ")

        self.load(self.path)

    def __del__(self):
        if self.config_changed:
            self.save()

    def save(self, path=None):
        if not path:
            path = self.path

        with click.open_file(path, mode="w+") as f:
            f.write(json.dumps(self.config, sort_keys=True, indent=4))
        self.hash = self.calculate_hash()
        self.config_changed = False

    def load(self, path=None):
        if not path:
            path = self.path

        with click.open_file(path) as f:
            self.config = self.validate(json.load(f))
            # validate(schema=JSON_CONFIG_SCHEMA, instance=self.config)
        self.hash = self.calculate_hash()

    def validate(self, config=None):
        if config is None:
            config = self.config

        for source in config["sources"]:
            if not source["enabled"]:
                continue
            type_ = SourceType.from_str(source["type"])
            if type_ is SourceType.JSON_PATH:
                path = source["path"]
                if os.path.isfile(path) and path.endswith(".json"):
                    continue
                elif os.path.isdir(path):
                    continue
                else:
                    out_warn(f"Path '{path}' is not a valid file or dir - disabling")
            elif type_ in (
                SourceType.JSON_URL,
                SourceType.TIMEDATE,
                SourceType.ISO_CURRENCY,
            ):
                url = source["url"]
                if not is_url_valid(url):
                    out_warn(f"Invalid url ('{url}') in config - disabling")
                elif not is_url_online(url):
                    out_warn(f"Unreachable url ('{url}') in config - disabling")
                else:
                    continue
            elif type_ is SourceType.CONFLUENCE_TABLE:
                url = source["url"]
                if not is_url_valid(url):
                    out_warn(f"Invalid url ('{url}') in config - disabling")
                else:
                    continue
            else:  # Unkown type, skip
                out_warn(f"Unknown source typ")

            source["enabled"] = False
            self.config_changed = True

        return config

    def changed(self) -> bool:
        return self.hash != self.calculate_hash()

    def calculate_hash(self):
        hash_object = hashlib.md5(json.dumps(self.config).encode("UTF-8"))
        return hash_object.hexdigest()

    def get_enabled_sources(self) -> List[Tuple[SourceType, Any]]:
        return [source for source in self.config["sources"] if source["enabled"]]

    def add_url(self, input):
        for source in self.config["sources"]:
            type_ = SourceType.from_str(source["type"])
            if type_ == SourceType.JSON_URL and input == source["url"]:
                # already exists
                out_warn(f"Url ('{input}') already in config - ignore")
                return

        self.config["sources"].append(
            {"enabled": True, "url": input, "type": "JSON_URL"}
        )

    def add_path(self, input):
        for source in self.config["sources"]:
            type_ = SourceType.from_str(source["type"])
            if type_ == SourceType.JSON_PATH and input == source["path"]:
                # already exists
                out_warn(f"Path ('{input}') already in config - ignore")
                return

        self.config["sources"].append(
            {"enabled": True, "path": input, "type": "JSON_PATH"}
        )

    def add_source(self, input):
        if os.path.isfile(input) or os.path.isdir(input):
            self.add_path(input)
        elif is_url_valid(input):
            self.add_url(input)

    def remove_source(self, input):
        for source in self.config["sources"]:
            if "url" in source:
                if input == source["url"]:
                    self.config["sources"].remove(source)
            elif "path" in source:
                if input == source["path"]:
                    self.config["sources"].remove(source)

    def config_menu(self):
        while True:
            click.clear()
            print("  #   | ON  | SOURCE")
            for id, source in enumerate(self.config["sources"]):
                type_ = SourceType.from_str(source["type"])
                menu_str = f"{id:3}   |"
                menu_str += " [X] |" if source["enabled"] else " [ ] |"
                if "url" in source:
                    menu_str += f" {source['url']}"
                elif "path" in source:
                    menu_str += f" {source['path']}"
                print(menu_str)

            print(f"q: quit")
            user_in = input("Item or 'q' to quit:")

            if user_in == "q":
                break

            for id, source in enumerate(self.config["sources"]):
                if str(id) == user_in:
                    source["enabled"] = not source["enabled"]
