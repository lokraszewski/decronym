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
from collections import defaultdict
from .lookup import *
from .result import *
from .config import *
import click
from datetime import datetime
from functools import lru_cache, partial, wraps
import toml
import os
import textwrap
import time
import json
from json import JSONEncoder
import random
import jsonpickle
import re
import math
import hashlib


out = partial(click.secho, bold=False, err=True)
err = partial(click.secho, fg="red", err=True)
out_green = partial(click.secho, bold=True, fg="green", err=True)


def callback_config(ctx, param, value):
    """Inject configuration from configuration file."""
    ctx.obj = Config(path=value)
    return value


@click.group()
@click.pass_context
@click.option(
    "--config",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, path_type=str
    ),
    is_eager=True,
    callback=callback_config,
    help=(f"Path to the config file to use."),
)
def cli(ctx, config):
    """<name pending> CLI"""
    pass


@cli.command()
@click.pass_context
@click.argument("acronyms", nargs=-1, required=True)
@click.option(
    "--tag",
    "-t",
    "tags",
    multiple=True,
    type=str,
    help=("Only show matches with given tags."),
)
def find(ctx, acronyms, tags):
    """Searches for acronyms in provided souces."""
    # First build a list of files that are being searched.
    all_matches = defaultdict(list)
    for lut in create_all_luts(ctx.obj):
        for acronym in acronyms:
            matches = lut[acronym]
            # Filter the results if the user has given any tags.
            # If any of the tags matches, the result will be shown.
            if tags and matches:
                matches = [r for r in matches if not set(r.tags).isdisjoint(tags)]
            if matches:
                all_matches[acronym] = matches + all_matches[acronym]

    for acronym, matches in all_matches.items():
        if matches:
            click.secho(acronym, bold=True, fg="green")
            for match in matches:
                if type(match) is Result:
                    print(match.pretty())
        else:
            # Add tag handling.
            err(f"No entires for '{acronym}' found!")


def test(path, data):
    with click.open_file(path, mode="w+") as f:
        f.write(json.dumps(data))


@cli.command()
@click.pass_context
def clean(ctx):
    """Cleans local cache"""

    luts = create_all_luts(config=ctx.obj)
    with click.progressbar(
        os.walk(os.path.abspath(ctx.obj.get_cache_dir())),
        label="Cleaning cache",
        fill_char=click.style("#", fg="green"),
        length=len(luts),
    ) as bar:
        for dir, _, files in bar:
            for file in files:
                cache_file = os.path.join(dir, file)
                if os.path.exists(cache_file):
                    os.remove(cache_file)


@cli.command()
@click.pass_context
def update(ctx):
    """Updates locally cached definition files based on config. """
    luts = create_all_luts(config=ctx.obj)
    with click.progressbar(
        luts,
        label="Updating cache",
        fill_char=click.style("#", fg="green"),
        length=len(luts),
    ) as bar:
        for lut in bar:
            lut.update_cache()


@cli.command()
@click.option(
    "--add",
    multiple=True,
    type=str,
    help=("Adds source to config"),
)
@click.option(
    "--thirdparty",
    is_flag=True,
    help=("Configure third party providers."),
)
@click.option(
    "--remove",
    is_flag=True,
    help=("Prompts a remove menu"),
)
@click.option(
    "--edit",
    is_flag=True,
    help=("Opens the config file for editing "),
)
@click.pass_context
def config(ctx, add, remove, thirdparty, edit):
    """Configuration helper."""

    if edit:
        click.edit(filename=ctx.obj.path)
        return
    elif remove:
        ctx.obj.click_config_remove()
    elif thirdparty:
        ctx.obj.click_config_thirdparty()
    elif add:
        for input in add:
            ctx.obj.add_source(input)

    if ctx.obj.changed() and click.confirm(f"Config changed, save changes?"):
        ctx.obj.save()
