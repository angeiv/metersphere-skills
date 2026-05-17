import unittest
from unittest import mock

from skills.scripts import ms_client
from skills.scripts import ms_case_report_md
from skills.scripts import ms_review_summary


class ReportTests(unittest.TestCase):
    def setUp(self):
        ms_review_summary.reset_caches()

    def test_review_summary_uses_2x_review_paths(self):
        self.assertEqual(ms_review_summary.CASE_LIST_PATH, "/track/test/case/list/{goPage}/{pageSize}")
        self.assertEqual(ms_review_summary.CASE_REVIEW_LIST_PATH, "/track/test/case/review/list/{goPage}/{pageSize}")
        self.assertEqual(ms_review_summary.REVIEW_CASE_LIST_PATH, "/track/test/review/case/list/{goPage}/{pageSize}")

    @mock.patch("skills.scripts.ms_review_summary.ms_client.paginated_post")
    @mock.patch("skills.scripts.ms_review_summary.ms_client.get_config")
    def test_fetch_case_reviews_builds_reverse_index_from_review_cases(self, get_config_mock, paginated_post_mock):
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
        paginated_post_mock.side_effect = [
            [
                {
                    "id": "r1",
                    "name": "登录评审",
                    "status": "Finished",
                    "createTime": 10,
                    "endTime": 20,
                    "reviewers": [{"name": "alice"}],
                }
            ],
            [
                {
                    "caseId": "c1",
                    "name": "登录主流程",
                    "reviewStatus": "Pass",
                }
            ],
        ]
        reviews = ms_review_summary.fetch_case_reviews("p1", "c1")
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewId"], "r1")
        self.assertEqual(reviews[0]["reviewName"], "登录评审")
        self.assertEqual(reviews[0]["caseReviewStatus"], "Pass")
        self.assertEqual(reviews[0]["reviewerName"], "alice")
        self.assertEqual(paginated_post_mock.call_args_list[0].args[1], ms_review_summary.CASE_REVIEW_LIST_PATH)
        self.assertEqual(paginated_post_mock.call_args_list[1].args[1], ms_review_summary.REVIEW_CASE_LIST_PATH)

    @mock.patch("skills.scripts.ms_review_summary.ms_client.request_json_soft", return_value=None)
    @mock.patch("skills.scripts.ms_review_summary.ms_client.get_config")
    def test_fetch_case_bugs_falls_back_to_issue_list_when_endpoint_errors(self, get_config_mock, _request_json_mock):
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
        bugs = ms_review_summary.fetch_case_bugs("p1", "c1", {"issueList": [{"id": "bug-1"}]})
        self.assertEqual(bugs, [{"id": "bug-1"}])

    def test_markdown_render_contains_sections(self):
        markdown = ms_case_report_md.md_lines(
            {
                "summary": {
                    "name": "登录主流程",
                    "caseId": "c1",
                    "num": 1,
                    "moduleName": "认证",
                    "priority": "P0",
                    "stepModel": "STEP",
                    "reviewStatus": "PASS",
                    "lastExecuteResult": "SUCCESS",
                    "reviewed": True,
                    "bugCount": 0,
                    "caseReviewCount": 1,
                },
                "detail": {
                    "prerequisite": "系统正常运行",
                    "description": "说明",
                    "steps": [{"desc": "操作", "result": "成功"}],
                },
                "bugs": [],
                "reviews": [{"reviewId": "r1", "reviewName": "登录评审", "reviewStatus": "PASS", "caseReviewStatus": "PASS"}],
            }
        )
        self.assertIn("## 用例摘要", markdown)
        self.assertIn("## 缺陷", markdown)
        self.assertIn("## 评审记录", markdown)


if __name__ == "__main__":
    unittest.main()
