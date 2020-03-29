import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workbench_utils import validate_language_code


class TestValidateLanguageCode(unittest.TestCase):

    def test_validate_code_in_list(self):
        res = validate_language_code('es')
        self.assertTrue(res)

    def test_validate_code_not_in_list(self):
        res = validate_language_code('foo')
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
