# -*- coding: utf-8 -*-
import os
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from decronym.cache import *

class ResultTestSuite(unittest.TestCase):
    """Tests the ResultCache class """
    def setUp(self):
        self.dir = os.path.dirname(os.path.abspath(__file__))

    def test_valid_cache_file(self):
        path = os.path.join(self.dir, 'data/cache_ok.json')
        cache = ResultCache(path = path)

        self.assertTrue('dma' in cache)
        self.assertTrue(len(cache['dma']) == 2 )

        for i, r in enumerate(cache['dma']):
            with self.subTest(i=i):
                self.assertIs(type(r), Result )

        self.assertEqual( cache['doesnotexist'], [])

    def test_bad_cache_file(self):
        path = os.path.join(self.dir, 'data/cache_bad_json.json')
        with self.assertRaises(json.JSONDecodeError):
            _ = ResultCache(path = path)

    def test_bad_cache_schema(self):
        path = os.path.join(self.dir, 'data/cache_bad_schema.json')

        # broken cache will ignore the results and setup empty cache file. A warning will be printed.
        cache = ResultCache(path = path)

        # no results for 'dma' despite the key being present in the file
        self.assertFalse('dma' in cache)


if __name__ == "__main__":
    unittest.main()
