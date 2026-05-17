import unittest
from contextlib import redirect_stderr
from io import StringIO

from skills.scripts import ms_client


class ClientMappingTests(unittest.TestCase):
    def test_workspace_resource_is_native_2x_name(self):
        self.assertEqual(ms_client.normalize_resource("workspace"), "workspace")

    def test_organization_resource_is_rejected(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                ms_client.resource_paths("organization")

    def test_functional_case_2x_paths(self):
        paths = ms_client.resource_paths("functional-case")
        self.assertEqual(paths["list"], "/track/test/case/list/{goPage}/{pageSize}")
        self.assertEqual(paths["get"], "/track/test/case/get/{testCaseId}")
        self.assertEqual(paths["create"], "/track/test/case/add")

    def test_project_list_prefers_workspace_endpoint(self):
        self.assertEqual(ms_client.project_list_path("ws-1"), "/project/project/listAll/ws-1")
        self.assertEqual(ms_client.project_list_path(""), "/project/project/list/all")

    def test_api_module_path_uses_protocol(self):
        self.assertEqual(ms_client.api_module_path("p1", "HTTP"), "/api/api/module/list/p1/HTTP")

    def test_normalize_body_maps_keyword_to_name(self):
        config = ms_client.MeterSphereConfig(
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
        body = ms_client.normalize_body("api", '{"keyword":"用户"}', config)
        self.assertEqual(body["name"], "用户")
        self.assertEqual(body["protocol"], "HTTP")
        self.assertEqual(body["versionId"], "v1")

    def test_normalize_body_rejects_organization_id(self):
        config = ms_client.MeterSphereConfig(
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
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                ms_client.normalize_body("project", '{"organizationId":"legacy"}', config)


if __name__ == "__main__":
    unittest.main()
