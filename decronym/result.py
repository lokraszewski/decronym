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


class Result(object):
    def __init__(self, acro: str,
                 full: str,
                 tags: List[str] = [],
                 comment: str = "",
                 source: str = "") -> None:
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
                out += click.style(letter,  bold=True)
        out += "\n"

        if self.comment:
            lines = textwrap.wrap(self.comment)
            for line in lines:
                out += click.style(f"\t{line}\n", fg="white")

        if self.tags:
            tags_formatted = " ".join(
                [f"[{tag}]" for tag in self.tags])
            out += click.style(f"\t{tags_formatted}\n", fg="green")

        if self.source:
            out += click.style(f"\tfrom: {self.source}\n", fg="blue")

        return out

    @classmethod
    def fromJSON(cls, json_dict: Dict, meta: Dict={}, source=''):
        key = json_dict['acro']
        src = meta.get('source', source)
        return cls(acro=key,
                   full=json_dict['full'],
                   tags=json_dict.get('tags', [])+meta.get('tags', []),
                   comment=json_dict.get('comment', ''),
                   source=src,
                   )
