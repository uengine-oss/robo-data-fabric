import os
import unittest
from unittest.mock import patch

from shared.config.settings import _bounded_int, _strict_bool


class FabricSettingsTest(unittest.TestCase):
    def test_boolean_parser_is_fail_closed(self):
        with patch.dict(os.environ, {"ROBO_TEST_BOOL": "yes"}):
            with self.assertRaises(ValueError):
                _strict_bool("ROBO_TEST_BOOL", False)
        with patch.dict(os.environ, {"ROBO_TEST_BOOL": "TRUE"}):
            self.assertTrue(_strict_bool("ROBO_TEST_BOOL", False))

    def test_port_parser_enforces_network_bounds(self):
        with patch.dict(os.environ, {"ROBO_TEST_PORT": "0"}):
            with self.assertRaises(ValueError):
                _bounded_int("ROBO_TEST_PORT", 8404, 1, 65535)
        with patch.dict(os.environ, {"ROBO_TEST_PORT": "8404"}):
            self.assertEqual(_bounded_int("ROBO_TEST_PORT", 1, 1, 65535), 8404)


if __name__ == "__main__":
    unittest.main()
