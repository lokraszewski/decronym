# -*- coding: utf-8 -*-
from collections import defaultdict
import hashlib
import os
import requests
import json
from jsonschema import validate, ValidationError
import click
from lxml import etree
import re
from .result import Result
from .config import get_cache_dir, is_valid_json_def, Config

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


def url_to_filename(url: str):
    hash_object = hashlib.md5(url.encode('utf-8'))
    return f"{hash_object.hexdigest()}.json"


class LookupBase(object):
    def load(self, force=False) -> None:
        pass

    def update_cache(self) -> None:
        pass

    def drop(self):
        pass

    def __getitem__(self, key) -> List[Result]:
        return []


class LookupRemoteJSON(LookupBase):
    def __init__(self, url):
        self.url = url
        self.cache_filepath = os.path.join(
            get_cache_dir(), url_to_filename(url))
        self.lut = defaultdict(list)

    def load(self, force=False) -> None:
        # first check if cache file exists
        if not os.path.isfile(self.cache_filepath) or force:
            self.update_cache()

        if len(self.lut) == 0 or force:
            with click.open_file(self.cache_filepath) as f:
                json_raw = json.load(f)
                if(is_valid_json_def(json_raw)):
                    # For now use a simple lookup with a dictionary of lists.
                    for _, entry in json_raw.items():
                        self.lut[entry['acro']].append(
                            Result.fromJSON(entry, source=self.url))

    def update_cache(self, force=False) -> None:
        req = requests.get(self.url)
        decoded_data = json.loads(req.text)
        
        directory = os.path.dirname(self.cache_filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)
                
        with click.open_file(self.cache_filepath, mode="w+") as f:
            f.write(json.dumps(decoded_data))

    def drop(self):
        self.lut = None

    def __getitem__(self, key):
        if len(self.lut) == 0:
            self.load()
        return self.lut.get(key, [])


class LookupLocalJSON(LookupBase):
    def __init__(self, filepath):
        self.filepath = filepath
        self.lut = defaultdict(list)

    def load(self, force=False) -> None:
        if len(self.lut) == 0 or force:
            with click.open_file(self.filepath) as f:
                json_raw = json.load(f)
                if(is_valid_json_def(json_raw)):
                    # For now use a simple lookup with a dictionary of lists.
                    for _, entry in json_raw.items():
                        self.lut[entry['acro']].append(
                            Result.fromJSON(entry, source=self.url))

    def drop(self):
        self.lut = defaultdict(list)

    def __getitem__(self, key) -> List[Result]:
        if len(self.lut) == 0:
            self.load()
        return self.lut.get(key, [])


class LookupSilmaril(LookupBase):
    def __init__(self, uri):
        self.uri = uri

    def __getitem__(self, key) -> List[Result]:
        root = etree.fromstring(requests.get(
            f"{self.uri}?{key}").text.encode("UTF-8"))

        return [Result(key,
                       full=acro.findtext('expan', default=''),
                       comment=acro.findtext('comment', default=''),
                       source=self.uri
                       ) for acro in root.findall('.//acro')]


def create_all_luts(config: Config) -> List[Any]:
    """Creates a list of LUTs from the given configuration. Assumes the configuration has been validated

    Args:
        config (Config): Configuration object

    Returns:
        List(LookupBase): List of LUTs
    """
    luts = []
    for url in config.get_urls():
        luts.append(LookupRemoteJSON(url))

    for path in config.get_paths():
        if os.path.isfile(path):
            luts.append(LookupLocalJSON(path))
        elif os.path.isdir(path):
            for dirpath, _, files in os.walk(os.path.abspath(path)):
                for file in files:
                    if file.endswith('.json'):
                        luts.append(
                            LookupLocalJSON(os.path.join(dirpath, file)))

    silmaril_config = config.get_third_party('silmaril')
    if silmaril_config and silmaril_config['enable']:
        luts.append(LookupSilmaril(silmaril_config['uri']))
    return luts
