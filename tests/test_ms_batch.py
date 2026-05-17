import unittest
from unittest import mock

from skills.scripts import ms_batch
from skills.scripts import ms_client


class BatchTests(unittest.TestCase):
    def test_definition_create_path_is_2x(self):
        self.assertEqual(ms_batch.API_DEFINITION_CREATE_PATH, "/api/api/definition/create")
        self.assertEqual(ms_batch.API_TEST_CASE_CREATE_PATH, "/api/api/testcase/create")

    @mock.patch("skills.scripts.ms_batch.ms_client.multipart_request")
    @mock.patch("skills.scripts.ms_batch.ms_client.get_config")
    def test_api_definition_id_is_backfilled_to_cases(self, get_config_mock, multipart_request_mock):
        get_config_mock.return_value = ms_client.MeterSphereConfig(
            base_url="http://example.test",
            access_key="ak",
            secret_key="sk",
            headers_json="",
            project_id="p1",
            workspace_id="ws1",
            protocol="HTTP",
            page_size=20,
            default_version_id="v1",
        )
        multipart_request_mock.side_effect = [
            {"data": {"id": "api-1"}},
            {"data": {"id": "case-1"}},
        ]
        bundle = {
            "definitions": [
                {
                    "projectId": "p1",
                    "moduleId": "module1",
                    "versionId": "v1",
                    "request": {},
                    "response": "{}",
                }
            ],
            "cases": [
                [
                    {
                        "projectId": "p1",
                        "versionId": "v1",
                        "request": {},
                        "response": "{}",
                    }
                ]
            ],
        }
        results = ms_batch.create_api_definitions_and_cases(bundle)
        self.assertEqual(results[0]["definition"]["data"]["id"], "api-1")
        self.assertEqual(multipart_request_mock.call_args_list[1].args[2], "/api/api/testcase/create")
        self.assertEqual(multipart_request_mock.call_args_list[1].args[3]["apiDefinitionId"], "api-1")


if __name__ == "__main__":
    unittest.main()
