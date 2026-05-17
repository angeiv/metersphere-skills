import unittest
from unittest import mock

from skills.scripts import ms_generate


class ApiGenerateTests(unittest.TestCase):
    @mock.patch("skills.scripts.ms_generate.resolve_version_for_draft", return_value="v1")
    def test_openapi_import_outputs_2x_definition_and_case(self, _version_mock):
        bundle = ms_generate.build_openapi_import(
            "p1",
            "module1",
            '{"openapi":"3.0.0","paths":{"/login":{"post":{"summary":"登录"}}}}',
        )
        definition = bundle["definitions"][0]
        case = bundle["cases"][0][0]
        self.assertEqual(definition["moduleId"], "module1")
        self.assertEqual(definition["protocol"], "HTTP")
        self.assertEqual(definition["versionId"], "v1")
        self.assertIn("request", definition)
        self.assertIn("request", case)
        self.assertEqual(case["versionId"], "v1")


if __name__ == "__main__":
    unittest.main()
