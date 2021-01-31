# -*- coding: utf-8 -*-

from .context import *

import os
from jsonschema import  ValidationError
import json

import unittest
class ResultTestSuite(unittest.TestCase):
    """Tests the Result class """
    def setUp(self):
        self.dir = os.path.dirname(os.path.abspath(__file__))

    def test_loading_defs_from_valid_json(self):
        path = os.path.join(self.dir, 'data/valid.json')
        items = Result.load_all_from_file(path)
        self.assertTrue(items)

        for i, item in enumerate(items):
            with self.subTest(i=i):
                self.assertIsInstance(item, Result)
                self.assertIn('GLOBAL_OPTIONAL', item.tags)
                self.assertIsNotNone( item.acro)
                self.assertIsNotNone( item.full)


    def test_missing_defs_in_json(self):
        path = os.path.join(self.dir, 'data/missing_defs.json')
        with self.assertRaises(ValidationError) as cm:
            _ = Result.load_all_from_file(path)

    def test_bad_json(self):
        path = os.path.join(self.dir, 'data/bad.json')
        with self.assertRaises(json.decoder.JSONDecodeError) as cm:
            _ = Result.load_all_from_file(path)


    def test_meta_optional(self):
        path = os.path.join(self.dir, 'data/meta_optional.json')
        items = Result.load_all_from_file(path)
        self.assertTrue(items)

        for i, item in enumerate(items):
            with self.subTest(i=i):
                self.assertIsInstance(item, Result)

if __name__ == "__main__":
    unittest.main()
