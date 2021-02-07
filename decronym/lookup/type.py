# -*- coding: utf-8 -*-

from enum import Enum, auto

class LookupType(Enum):
    JSON_PATH = "json_path"
    JSON_URL = "json_url"
    TIMEDATE = "timedate"
    ISO_CURRENCY = "iso_currency"
    CONFLUENCE_TABLE = "confluence_table"
    WIKIPEDIA = "wikipedia"

    def __deepcopy__(self, _):
        return self.value

    # @classmethod
    # def from_str(cls, label):
    #     if label in ("json_path"):
    #         return cls.JSON_PATH
    #     elif label in ("json_url"):
    #         return cls.JSON_URL
    #     elif label in ("timedate"):
    #         return cls.TIMEDATE
    #     elif label in ("iso_currency"):
    #         return cls.ISO_CURRENCY
    #     elif label in ("confluence_table"):
    #         return cls.CONFLUENCE_TABLE
    #     else:
    #         raise NotImplementedError

    # @classmethod
    # def to_str(cls, enum_):
    #     map = {
    #         cls.JSON_PATH: "json_path",
    #         cls.JSON_URL: "json_url",
    #         cls.TIMEDATE: "timedate",
    #         cls.ISO_CURRENCY: "iso_currency",
    #         cls.CONFLUENCE_TABLE: "confluence_table",
    #     }
    #     return map[enum_]
