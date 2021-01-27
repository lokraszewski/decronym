# -*- coding: utf-8 -*-

from setuptools import setup, find_packages, Extension
from os import path
import os

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="decronym",
    version="0.0.1a0",
    description="Because TLAs can be such a PITA!",
    author="Lukasz Okraszewski",
    author_email="lokraszewski.work@gmail.com",
    url="https://github.com/lokraszewski/decronym",
    project_urls={
        "Source": "https://github.com/lokraszewski/decronym",
        "Tracker": "https://github.com/lokraszewski/decronym/issues",
    },
    license="MIT License",
    packages=find_packages(exclude=("tests", "docs")),
    package_data={
        "decronym": [
            "config.toml",
        ]
    },
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": ["decronym=decronym:cli"],
    },
    long_description_content_type="text/markdown",
    long_description=long_description,
    install_requires=[
        "click",
        "requests",
        "jsonpickle",
        "jsonschema",
        "requests",
        "toml",
        "lxml",
    ],
)
