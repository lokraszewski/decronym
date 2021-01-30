# -*- coding: utf-8 -*-
import hashlib
import os
import requests
import json
from jsonschema import validate, ValidationError
import click
from lxml import etree
import textwrap
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

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "optional": True,
        },
        "defs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "acro": {"type": "string"},
                    "full": {"type": "string"},
                    "comment": {"type": "string"},
                    "suggested": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["acro", "full"],
            },
        },
    },
    "required": ["defs"],
}


class Result(object):
    def __init__(
        self,
        acro: str,
        full: str,
        tags: List[str] = [],
        comment: str = "",
        source: str = "",
    ) -> None:
        self.acro = acro
        self.full = full
        self.tags = tags
        self.comment = comment
        self.source = source

    def pretty(self):
        out = "\t"
        for letter in self.full:
            if letter.isupper():
                out += click.style(letter, bold=True, fg="green")
            else:
                out += click.style(letter, bold=True)
        out += "\n"

        if self.comment:
            lines = textwrap.wrap(self.comment)
            for line in lines:
                out += click.style(f"\t{line}\n", fg="white")

        if self.tags:
            tags_formatted = " ".join([f"[{tag}]" for tag in self.tags])
            out += click.style(f"\t{tags_formatted}\n", fg="green")

        if self.source:
            out += click.style(f"\tfrom: {self.source}\n", fg="blue")

        return out

    def __str__(self) -> str:
        return self.to_dict().__str__()

    def to_dict(self):
        return {
            "acro": self.acro,
            "full": self.full,
            "tags": self.tags,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, json_dict: Dict, meta: Dict = {}):
        return cls(
            acro=json_dict["acro"],
            full=json_dict["full"],
            tags=json_dict.get("tags", []) + meta.get("tags", []),
            comment=json_dict.get("comment", ""),
            source=meta.get("source", None),
        )

    @classmethod
    def load_all_from_dict(cls, dict):
        validate(schema=JSON_SCHEMA, instance=dict)
        return [
            Result.from_dict(item, meta=dict["meta"] if "meta" in dict else {})
            for item in dict["defs"]
        ]

    @classmethod
    def load_all_from_json_str(cls, json_str):
        json_data = json.loads(json_str)
        return cls.load_all_from_dict(json_data)

    @classmethod
    def load_all_from_file(cls, path):
        with click.open_file(path) as f:
            json_data = json.load(f)

        return cls.load_all_from_dict(json_data)

    @classmethod
    def save_to_json(cls, path, items, meta={}):
        data_out = {"meta": meta, "defs": [item.to_dict() for item in items]}
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with click.open_file(path, mode="w+") as f:
            f.write(json.dumps(data_out))