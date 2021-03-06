# -*- coding: utf-8 -*-
import os
import click
import json
import hashlib

from jsonschema import validate, ValidationError
from pkg_resources import resource_filename
from .util import *
from .lookup.type import LookupType

# from lookup import *
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
    "definitions": {
        "source": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "source": {"type": "string"},
                "type": {"type": "string"},
                "extra": {"type": "object"},
            },
            "required": ["type", "source", "enabled"],
        }
    },
    
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/source"
            }
        },
        "tag_map" : {
            "type" : "object"
        }
    }
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


class Config(object):
    """Stores configuration"""

    def __init__(self, path=None) -> None:
        self.config_ = None
        self.hash = None
        self.config_changed = False
        self.path = select_config_file(path)

        # Check if any valid path has beeen given.
        if not self.path:
            raise click.UsageError(f"No valid config found. ")

        self.load(self.path)

    def __del__(self):
        if self.config_ is not None and self.changed() and click.confirm(f"Config changed, save changes?"):
            self.save()

    def save(self, path=None):
        if not path:
            path = self.path

        with click.open_file(path, mode="w+") as f:
            f.write(json.dumps(self.config_, sort_keys=True, indent=4))
        self.hash = self.calculate_hash()
        self.config_changed = False

    def load(self, path=None):
        if not path:
            path = self.path

        with click.open_file(path) as f:
            try:
                json_data = json.load(f)
                validate(instance=json_data, schema=JSON_CONFIG_SCHEMA)
                self.config_ = json_data
            except ValidationError as e:
                print(e)
                raise click.UsageError(f"Invalid configuration format, exiting.")

        self.hash = self.calculate_hash()

    def changed(self):
        return self.hash != self.calculate_hash()

    def calculate_hash(self):
        hash_object = hashlib.md5(json.dumps(self.config_).encode("UTF-8"))
        return hash_object.hexdigest()

    def add_source(self, new_type: LookupType, new_source: str, new_extra: Dict = None):
        for type_, source, _, _ in self.get_sources():
            if new_type == type_ and new_source == source:
                out_warn(f"{new_type} - {new_source} - already in config!")
                return

        self.config_["sources"].append(
            {
                "type": new_type.value,
                "source": new_source,
                "enabled": True,
                "extra": new_extra,
            }
        )

    def config_menu(self):
        while True:
            click.clear()
            print("  #   | ON  | SOURCE")
            for id, source in enumerate(self.config_["sources"]):
                menu_str = f"{id:3}   |"
                menu_str += " [X] |" if source["enabled"] else " [ ] |"
                menu_str += f" {source['source']}"
                print(menu_str)

            print(f"q: quit")
            user_in = input("Item or 'q' to quit:")

            if user_in == "q":
                break

            for id, source in enumerate(self.config_["sources"]):
                if str(id) == user_in:
                    source["enabled"] = not source["enabled"]

    def get_sources(self):
        return [
            (
                LookupType(source["type"]),
                source["source"],
                source["enabled"],
                source.get("extra", {}),
            )
            for source in self.config_["sources"]
        ]

    def get_tag_map(self):
        return self.config_.get("tag_map", {})
