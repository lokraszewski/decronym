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
from .filter import *
from .util import *

def callback_config(ctx, param, value):
    """Inject configuration from configuration file."""
    ctx.obj = Config(path=value)
    return value

def callback_type(ctx, param, value):
    if value is not None:
        return LookupType.from_str(value)
    return None

def guess_type(inout):
    if is_url_valid(input):
        if 'confluence' in input:
            type_ = LookupType.CONFLUENCE_TABLE
        else:
            type_ = LookupType.JSON_URL
    elif os.path.isfile(input) and input.endswith(".json"):
        type_ = LookupType.JSON_PATH
    elif os.path.isdir(input):
        type_ = LookupType.JSON_PATH

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
    lookups = LookupAggregate(luts = ctx.obj.get_luts())
    lookups.request(acronyms)
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
    
    new_source = {
        "type":type_.value,
        "enabled":True
        }

    if type_ is LookupType.JSON_PATH:
        new_source['path'] = input
    elif type_ in (
                LookupType.JSON_URL,
                LookupType.TIMEDATE,
                LookupType.ISO_CURRENCY,
                LookupType.CONFLUENCE_TABLE,
            ):
        if is_url_valid(input):
            new_source['url'] = input
        else:
            raise click.UsageError(f"Invalid URL given.")
        
    ctx.obj.add_source(new_source)

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

