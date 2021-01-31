# -*- coding: utf-8 -*-
import os
import click
import toml
import hashlib
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

def config_remove_menu(items, menu):
    click.clear()
    number_of_urls = len(items)

    if number_of_urls == 0:
        click.echo("No items found, going back")
        return (items, "source")

    go_back = number_of_urls + 1
    exit = go_back + 1
    for index, label in enumerate(items):
        click.echo(f"{index}: {label}")
    click.echo(f"{go_back}: back")
    click.echo(f"{exit}: exit")

    choice = int(
        click.prompt(
            "Please select:",
            type=click.Choice([str(i) for i in range(exit + 1)]),
            default=exit,
        )
    )

    if choice == go_back:
        menu = "source"
    elif choice == exit:
        menu = "quit"
    elif click.confirm(f"Removing {items[choice]} do you want to continue?"):
        items.remove(items[choice])
    return (items, menu)


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
    user = os.path.join(os.environ["HOME"], ".config/decronym", "config.toml")
    package_default = os.path.abspath(resource_filename("decronym", "config.toml"))

    for candidate in (path, user, package_default):
        if not candidate:
            continue
        if os.path.isfile(candidate) and candidate.endswith(".toml"):
            return candidate
    else:
        return None

class SourceType(Enum):
    JSON_PATH = auto()
    JSON_URL = auto()
    TIMEDATE = auto()
    ISO_CURRENCY = auto()

    @classmethod
    def from_str(cls, label):
        if label in ('path'):
            return cls.JSON_PATH
        elif label in ('url'):
            return cls.JSON_URL
        elif label in ('timeanddate'):
            return cls.TIMEDATE
        elif label in ('iso_currency'):
            return cls.ISO_CURRENCY
        else:
            raise NotImplementedError
class Config(object):
    """Stores configuration"""

    def __init__(self, path=None) -> None:
        self.path = select_config_file(path)

        # Check if any valid path has beeen given.
        if not self.path:
            raise click.UsageError(f"No valid config found. ")

        self.config = None
        self.hash = None
        self.load()
        self.config_changed = False

    def __del__(self):
        if self.config_changed:
            self.save()
            
    def save(self, path=None):
        if not path:
            path = self.path

        with click.open_file(path, mode="w+") as f:
            f.write(toml.dumps(self.config))
        self.hash = self.calculate_hash()

    def load(self, path=None):
        if not path:
            path = self.path

        try:
            self.config = toml.load(path)
            self.hash = self.calculate_hash()
        except (toml.TomlDecodeError, OSError) as e:
            raise click.FileError(
                filename=path, hint=f"Error reading configuration file: {e}"
            )

    def changed(self) -> bool:
        return self.hash != self.calculate_hash()

    def calculate_hash(self):
        hash_object = hashlib.md5(toml.dumps(self.config).encode("UTF-8"))
        return hash_object.hexdigest()

    def get_valid_sources(self) -> List[Tuple[SourceType, Any]]:
        sources = []
        for url in self.config["source"]["url"]:
            if not is_url_valid(url):
                out_warn(f"Invalid url ('{url}') in config - skipping")
            elif not is_url_online(url):
                out_warn(f"Unreachable url ('{url}') in config - skipping")
            else:
                sources.append((SourceType.JSON_URL, url))

        for path in self.config["source"]["path"]:
            if os.path.isfile(path) and path.endswith(".json"):
                sources.append((SourceType.JSON_PATH, path))         
            elif os.path.isdir(path):
                for dirpath, _, files in os.walk(os.path.abspath(path)):
                    for file in files:
                        if file.endswith(".json"):
                            sources.append((SourceType.JSON_PATH, os.path.join(dirpath, file)))         

        for name, conf in self.config["source"]["misc"].items():
            if conf['enable']:
                if 'url' in conf:
                    url = conf['url']
                    if not is_url_valid(url):
                        out_warn(f"Invalid url ('{url}') in config - skipping")
                    elif not is_url_online(url):
                        out_warn(f"Unreachable url ('{url}') in config - skipping")
                    else:
                        sources.append((SourceType.from_str(name), conf))   

        return sources

    def add_url(self, input):
        if input not in self.config["source"]["url"]:
            self.config["source"]["url"].append(input)

    def add_path(self, input):
        if input not in self.config["source"]["path"]:
            self.config["source"]["path"].append(input)

    def add_source(self, input):
        if is_url_valid(input):
            self.add_url(input)
        elif os.path.isfile(input) or os.path.isdir(input):
            self.add_path(input)

    def click_config_remove(self):
        menu = "source"
        source_menu = {"u": "url", "p": "path", "q": "quit"}

        click.clear()
        while True:
            if menu == "source":
                click.echo("Select type of source:")
                for k, label in source_menu.items():
                    click.echo(f"{k}: {label}")
                char = click.getchar()
                if char in source_menu:
                    menu = source_menu[char]
                else:
                    click.echo("Invalid input")
            elif menu == "url":
                items, menu = config_remove_menu(self.config["source"]["url"], menu)
                self.config["source"]["url"] = items
            elif menu == "path":
                items, menu = config_remove_menu(self.config["source"]["path"], menu)
                self.config["source"]["path"] = items
            else:  # quit and unhandled states just return
                break

