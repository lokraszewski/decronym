# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import click
import textwrap
from typing import (
    List,
)

@dataclass_json
@dataclass(unsafe_hash=True)
class Result(object):
    acronym: str
    full: str
    comment: str = ""
    source: str = field(default_factory=str, compare=False)
    tags: List[str] = field(default_factory=list, compare=False)

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
