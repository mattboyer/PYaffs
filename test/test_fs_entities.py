import unittest
from mock import Mock

import fs_entities

class Test_FSLeaf(unittest.TestCase):
    def setUp(self):
        self.fs = Mock()
        self.header = Mock()
        self.lead = fs_entities.FSLeaf(self.fs, self.header)

    def test_get_bytes(self):
        self.assertEquals(0, 0)
