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
from .lookup import *
from .result import *
from .config import Config
from .util import *

def callback_config(ctx, param, value):
    """Inject configuration from configuration file."""
    ctx.obj = Config(path=value)
    return value

def callback_type(ctx, param, value):
    if value is not None:
        return LookupType(value)
    return None

def guess_type(input:str):
    if is_url_valid(input):
        if 'confluence' in input:
            return LookupType.CONFLUENCE_TABLE
        elif 'timeanddate' in input:
            return LookupType.TIMEDATE
        elif 'currency-iso' in input:
            return LookupType.ISO_CURRENCY
        else:
            return LookupType.JSON_URL
    elif os.path.isfile(input) and input.endswith(".json"):
        return LookupType.JSON_FILE
    elif os.path.isdir(input):
        return LookupType.JSON_PATH

    return None

@click.group()
@click.pass_context
@click.option(
    "-c","--config",
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
    lookups = LookupAggregate(LookupFactory.from_config(ctx.obj))
    lookups.request(acronyms)
    if tags:
        lookups.filter_tags(tags)
    lookups.show_results()

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
@click.argument("input", required=True)
@click.option('--pageid',
              type=int,
              help=f"PageId required when adding '{LookupType.CONFLUENCE_TABLE.value}'"
              )
@click.option('--type','type_',
              type=click.Choice([t.value for t in LookupType],               
                                case_sensitive=False), 
              callback=callback_type
              )
def add(ctx, input, type_, pageid):
    """Adds source to config"""
    # Try to figure out type from input
    if type_ is None:
        type_ = guess_type(input)

    if type_ is None:
        raise click.UsageError(f"Could not figure out the source type from args, please specify with --type")
    elif type_ is LookupType.CONFLUENCE_TABLE and pageid is None:
        raise click.UsageError(f"Page ID is required for Confluence source")
    elif type_ in (
                LookupType.JSON_URL,
                LookupType.TIMEDATE,
                LookupType.ISO_CURRENCY,
                LookupType.CONFLUENCE_TABLE,
                LookupType.WIKIPEDIA
            ) and not is_url_valid(input):
        raise click.UsageError(f"Invalid URL given.")

    extra ={}
    if type_ is LookupType.CONFLUENCE_TABLE:
        extra["pageid"] = pageid
    elif type_ in (LookupType.JSON_FILE, LookupType.JSON_PATH):
        input = os.path.abspath(input)
        
    ctx.obj.add_source(type_, input, extra)

@cli.command()
@click.pass_context
def menu(ctx):
    """Displays menu to toggle which sources are used."""
    ctx.obj.config_menu()

@cli.command()
@click.pass_context
def edit(ctx):
    """Opens config in default editor."""
    click.edit(filename=ctx.obj.path)

@cli.command()
@click.pass_context
@click.argument(
    "out",
    type=click.Path(
        file_okay=True, 
        path_type=str,
        allow_dash=True
    ),
    default='-',
)
def dump(ctx, out):
    """Dumps config to file, by default writes to stdout"""
    ctx.obj.save(out)

