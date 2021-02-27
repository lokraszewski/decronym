# -*- coding: utf-8 -*-
import multiprocessing as mp
from jsonschema import validate, ValidationError
from collections import defaultdict
from typing import (
    List,
)

from ..config import Config
from ..util import *
from .base import Lookup, LookupType
from .jsonpath import LookupJsonPath
from .jsondir import LookupJsonDir
from .jsonremote import LookupRemote
from .timezone import LookupTimeAndDate
from .currency import LookupCurrency
from .confluence import LookupConfluenceTable
from .wikipedia import LookupWikipedia


_type_to_lookup = {
    LookupType.JSON_FILE: LookupJsonPath,
    LookupType.JSON_PATH: LookupJsonDir,
    LookupType.JSON_URL: LookupRemote,
    LookupType.TIMEDATE: LookupTimeAndDate,
    LookupType.ISO_CURRENCY: LookupCurrency,
    LookupType.CONFLUENCE_TABLE: LookupConfluenceTable,
    LookupType.WIKIPEDIA: LookupWikipedia,
}


class LookupFactory(object):
    @classmethod
    def create(cls, type, source, enabled, extra, config: Config = None):
        return _type_to_lookup[type](
            source=source, enabled=enabled, extra=extra, config=config
        )

    @classmethod
    def from_config(cls, config: Config):
        return [
            cls.create(type, source, enabled, extra, config)
            for type, source, enabled, extra in config.get_sources()
        ]


def _acronym_find_helper(lut, input):
    return (input, lut.find(input))


def _acronym_similar_helper(lut, input):
    return (input, lut.find_similar(input))


class LookupAggregate(object):
    def __init__(self, luts: List[Lookup]):
        self.luts = luts
        self.matches = defaultdict(list)
        self.filtered = defaultdict(list)
        self.similar = defaultdict(list)
        self.requests = []

    def append_match(self, results):
        for key, r in results:
            self.matches[key] += r

    def append_similar(self, results):
        for key, r in results:
            self.similar[key] += r

    def request(self, acronyms):
        self.requests += acronyms

        with mp.Pool() as pool:
            args = [(lut, a) for lut in self.luts for a in acronyms]
            pool.starmap_async(_acronym_find_helper, args, callback=self.append_match)
            pool.starmap_async(
                _acronym_similar_helper, args, callback=self.append_similar
            )
            pool.close()
            pool.join()

    def filter_tags(self, tags):
        flat_list = [item for list in self.matches.values() for item in list]
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
