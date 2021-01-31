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
import click
import os
import json
from functools import lru_cache, partial, wraps

from .lookup import *
from .result import *
from .config import Config
from .filter import *
from .util import get_cache_dir


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
    """Decronym CLI"""
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
    """Searches for acronyms."""

    lut = LookupCollector(ctx.obj)
    for acronym in acronyms:
        unfiltered = lut.find(acronym)
        matches, filtered = filter(unfiltered, tags=tags)

        if matches:
            click.secho(acronym, bold=True, fg="green")
            for match in matches:
                print(match.pretty())
        elif filtered:
            click.echo("Some entries filtered, try running without filters?")
        else:
            click.echo(f"No entires for '{acronym}' found!")
            similar = lut.find_similar(acronym)
            if similar:
                click.echo(f"Suggested: {set(similar)}")


@cli.command()
@click.pass_context
def clean(ctx):
    """Deletes all local cache files."""

    with click.progressbar(
        os.walk(os.path.abspath(get_cache_dir())),
        label="Cleaning cache",
        fill_char=click.style("#", fg="green"),
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

    # Create all sources with force flag enabled, this recreates cache files where relevant.
    luts = LookupFactory.from_config(ctx.obj)

    with click.progressbar(
        luts,
        label="Updating cache",
        fill_char=click.style("#", fg="green"),
        length=len(luts),
    ) as bar:
        for lut in bar:
            lut.load_from_source()
            lut.write_to_cache()


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
@click.option(
    "--dump",
    help=("Dumps the config to file (or stdout: '-' )"),
)
@click.pass_context
def config(ctx, add, remove, thirdparty, edit, dump):
    """Configuration helper."""
    if dump:
        ctx.obj.save(path=dump)
        return

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
