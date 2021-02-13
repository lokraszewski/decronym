# -*- coding: utf-8 -*-
import os
import requests
import json
import click
import re
import getpass

from jsonschema import validate, ValidationError
from collections import defaultdict
from lxml import etree
from enum import Enum, auto
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

from ..result import *
from ..util import *
from .base import Lookup, LookupType
from .jsonpath import LookupJsonPath
from .jsondir import LookupJsonDir
from .jsonremote import LookupRemote
from .timezone import LookupTimeAndDate
from .currency import LookupCurrency
from .confluence import LookupConfluenceTable
from .wikipedia import LookupWikipedia


class LookupFactory(object):
    @classmethod
    def from_json(cls, json_dict: Dict):
        type_ = LookupType(json_dict["type"])
        if type_ == LookupType.JSON_PATH:
            path=json_dict["path"]
            if os.path.isfile(path) and path.endswith(".json"):
                return LookupJsonPath(
                    type_=type_, 
                    path=path,
                    enabled=json_dict["enabled"]
                )
            elif os.path.isdir(path):
                return LookupJsonDir(
                    type_=type_, 
                    path=path,
                    enabled=json_dict["enabled"]
                )
            else:
                return None


        elif type_ == LookupType.JSON_URL:
            return LookupRemote(
                type_=type_, 
                url=json_dict["url"], 
                enabled=json_dict["enabled"]
            )
        elif type_ == LookupType.TIMEDATE:
            return LookupTimeAndDate(
                type_=type_, 
                url=json_dict["url"], 
                enabled=json_dict["enabled"]
            )
        elif type_ == LookupType.ISO_CURRENCY:
            return LookupCurrency(
                type_=type_, 
                url=json_dict["url"], 
                enabled=json_dict["enabled"]
            )
        elif type_ == LookupType.CONFLUENCE_TABLE:
            return LookupConfluenceTable(
                type_=type_, 
                url=json_dict["url"], 
                page_id=json_dict["page_id"], 
                enabled=json_dict["enabled"]
            )       
        elif type_ == LookupType.WIKIPEDIA:
            return LookupWikipedia(
                type_=type_, 
                url=json_dict["url"], 
                enabled=json_dict["enabled"]
            )
        else:
            out_err(f"Unknown type {type_} ")
            return None


class LookupAggregate(object):
    def __init__(self, luts:List[Lookup]):
        self.luts = luts
        self.matches = defaultdict(list)
        self.filtered = defaultdict(list)
        self.similar = defaultdict(list)
        self.requests = []

    def request(self, acronyms):
        for acronym in acronyms:
            if not is_acronym_valid(acronym):
                out_warn(f"'{acronym}' is not a valid acronym, skipping!")
                continue

            self.requests.append(acronym)
            for lut in self.luts:
                self.matches[acronym] += lut[acronym]
                self.similar[acronym] += lut.find(acronym,exact=False, similar=True)

    def filter_tags(self, tags):
        flat_list = [ item  for list in self.matches.values() for item in list]
        filtered = [r for r in flat_list if set(r.tags).isdisjoint(tags)]
        for item in filtered:
            self.filtered[item.acronym].append(item)
            if item in self.matches[item.acronym]:
                self.matches[item.acronym].remove(item)

    def show_results(self):
        for requested in self.requests:
            matched = self.matches[requested]
            filtered = self.filtered[requested]
            similar = self.similar[requested]
            if matched:
                out_success(requested)
                for match in matched:
                    print(match.pretty())
            elif filtered:
                out_warn("Some entries filtered, try running without filters?")
            else:
                out_warn(f"No entires for '{requested}' found!")
                if similar:
                    similar_formatted = " ".join([f"{s}" for s in set(similar)])
                    out(f"Suggested: {similar_formatted}")
