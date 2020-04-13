import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workbench_utils import compare_strings


class TestCompareStings(unittest.TestCase):

    def test_strings_match(self):
        res = compare_strings('foo', 'foo  ')
        self.assertTrue(res)
        res = compare_strings('foo', 'Foo')
        self.assertTrue(res)
        res = compare_strings('foo', 'Foo#~^.')
        self.assertTrue(res)
        res = compare_strings('foo bar baz', 'foo   bar	baz')
        self.assertTrue(res)

    def test_strings_do_not_match(self):
        res = compare_strings('foo', 'foot')
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
