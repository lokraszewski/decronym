# -*- coding: utf-8 -*-
import os
import click
import toml
import hashlib
import re
from jsonschema import validate, ValidationError
from pkg_resources import resource_filename
from enum import Enum, auto
from .util import is_url_valid


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

    def get_urls(self):
        return self.config["source"]["urls"]

    def get_paths(self):
        return self.config["source"]["paths"]

    def get_third_party(self, name):
        return self.config["source"][name]

    def set_third_party(self, name):
        pass

    def set_urls(self, urls):
        return []

    def set_paths(self, paths):
        return []

    def get_thirdparty_config(self, name, config={}):
        pass

    def set_thirdpartycon_config(self, name, config={}):
        pass

    def add_url(self, input):
        if input not in self.config["source"]["urls"]:
            self.config["source"]["urls"].append(input)

    def add_path(self, input):
        if input not in self.config["source"]["paths"]:
            self.config["source"]["paths"].append(input)

    def add_source(self, input):
        if is_url_valid(input):
            self.add_url(input)
        elif os.path.isfile(input) or os.path.isdir(input):
            self.add_path(input)

    def click_config_remove(self):
        menu = "source"
        source_menu = {"u": "urls", "p": "paths", "q": "quit"}

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
            elif menu == "urls":
                items, menu = config_remove_menu(self.config["source"]["urls"], menu)
                self.config["source"]["urls"] = items
            elif menu == "paths":
                items, menu = config_remove_menu(self.config["source"]["paths"], menu)
                self.config["source"]["paths"] = items
            else:  # quit and unhandled states just return
                break
        pass

    def click_config_thirdparty(self):
        click.clear()
        self.config["source"]["silmaril"]["enable"] = click.confirm(
            "Enable acronyms.silmaril.ie?",
            default=self.config["source"]["silmaril"]["enable"],
        )
