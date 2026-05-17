import unittest
from unittest import mock

from skills.scripts import ms_generate


class FunctionalGenerateTests(unittest.TestCase):
    @mock.patch("skills.scripts.ms_generate.resolve_version_for_draft", return_value="v1")
    def test_functional_case_draft_matches_2x_shape(self, _version_mock):
        cases = ms_generate.build_functional_cases("p1", "node1", "用户登录")
        self.assertTrue(cases)
        first = cases[0]
        self.assertEqual(first["projectId"], "p1")
        self.assertEqual(first["nodeId"], "node1")
        self.assertEqual(first["stepModel"], "STEP")
        self.assertEqual(first["versionId"], "v1")
        self.assertIn("steps", first)
        self.assertEqual(first["customFields"], "[]")


if __name__ == "__main__":
    unittest.main()
