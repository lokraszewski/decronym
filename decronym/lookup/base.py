# -*- coding: utf-8 -*-

import difflib

from .type import LookupType
from enum import Enum, auto
from ..util import *
from ..result import *

class Lookup(object):
    def __init__(self, value:str, type_: LookupType, enabled: bool = True):
        # Common between all types of lookup
        self.value = value
        self.valid = None
        self.enabled = enabled
        self.type = type_
        self.cache = ResultCache(self.cache_path())


    def validate(self):
        out_warn(f"{self}.validate() not implemented, validate will set to True by default.")
        self.valid = True

    def cache_path(self):
        hash_object = hashlib.md5(self.value.encode("utf-8"))
        dir = get_cache_dir()
        filename = f"{hash_object.hexdigest()}.json"
        return os.path.join(dir, filename)

    def to_dict(self) -> Dict:
        return {
            "enabled":self.enabled,
            "type":LookupType.to_str(self.type),
        }

    def is_enabled(self) -> bool:
        return self.enabled
        
    def is_valid(self) -> bool:
        if self.valid  is None:
            self.validate()

        return self.valid
    
    def find_direct(self, 
                    key: str) -> List[Result]:
        out_warn(f"{self}.find_direct() not implemented.")
        self.valid = False
        return []

    def find(self, key: str, exact:bool=True, similar:bool=False) -> List[Result]:

        # ensure key is lower case
        key = key.lower()

        if not exact and not similar:
            out_warn(f"{self} Neither exact not similar flags are set, no results will be returned.")

        # Configuration is invalid skipping 
        if not self.is_valid():
            out_warn(f"{self} is not valid, skipping")
            return []

        if not self.is_enabled():
            return []

        results = []
        # Check if we need to load.
        # if load is needed, try loading, 
        # Check if key is in cache, if it is, just return it!
        if exact:
            if key in self.cache:
                results += self.cache[key]
            else:
                results += self.find_direct(key)
                self.cache.add(results)

        # similar is only based on cache
        if similar:
            results += difflib.get_close_matches(key, self.cache.keys())

        return results

    def find_similar(self, key: str):
        return self.find(key, exact=False, similar=True)

    def __getitem__(self, key) :
        return self.find(key, exact=True, similar=False)
