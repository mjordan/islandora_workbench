import sys
import os
import unittest
from ruamel.yaml import YAML

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workbench_utils import split_typed_relation_string


class TestSplitTypedRelationString(unittest.TestCase):

    def test_split_typed_relation_string_single(self):
        config = {'subdelimiter': '|'}
        res = split_typed_relation_string(config, 'relators:pht:5', 'foo')
        self.assertDictEqual(res[0], {'target_id': int(5), 'rel_type': 'relators:pht', 'target_type': 'foo'})

    def test_split_typed_relation_string_multiple(self):
        config = {'subdelimiter': '|'}
        res = split_typed_relation_string(config, 'relators:pht:5|relators:con:10', 'bar')
        self.assertDictEqual(res[0], {'target_id': int(5), 'rel_type': 'relators:pht', 'target_type': 'bar'})
        self.assertDictEqual(res[1], {'target_id': int(10), 'rel_type': 'relators:con', 'target_type': 'bar'})

    def test_split_typed_relation_string_multiple_at_sign(self):
        config = {'subdelimiter': '@'}
        res = split_typed_relation_string(config, 'relators:pht:5@relators:con:10', 'baz')
        self.assertDictEqual(res[0], {'target_id': int(5), 'rel_type': 'relators:pht', 'target_type': 'baz'})
        self.assertDictEqual(res[1], {'target_id': int(10), 'rel_type': 'relators:con', 'target_type': 'baz'})


if __name__ == '__main__':
    unittest.main()
