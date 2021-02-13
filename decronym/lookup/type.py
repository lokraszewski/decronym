# -*- coding: utf-8 -*-

from enum import Enum

class LookupType(Enum):
    JSON_FILE = "json_file"
    JSON_URL = "json_url"
    JSON_PATH = "path"
    TIMEDATE = "timedate"
    ISO_CURRENCY = "iso_currency"
    CONFLUENCE_TABLE = "confluence_table"
    WIKIPEDIA = "wikipedia"

    def __deepcopy__(self, _):
        return self.value
