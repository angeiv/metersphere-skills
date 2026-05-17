#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills.scripts import ms_client


def usage() -> None:
    print(
        """ms — MeterSphere 2.x CLI

用法:
  ms <resource> <action> [args...]
  ms raw <METHOD> <PATH> [JSON]
  ms reviewed-summary <projectId> [keyword]
  ms case-report <projectId> <caseId>
  ms case-report-md <projectId> <caseId>

资源:
  workspace
  project
  functional-module
  functional-template
  api-module
  functional-case
  functional-case-review
  case-review
  case-review-detail
  case-review-module
  case-review-user
  api
  api-case

动作:
  list [关键词|JSON]
  get <id>
  create <JSON>

示例:
  ms workspace list
  ms project list
  ms project list <workspaceId>
  ms functional-module list <projectId>
  ms functional-template list <projectId>
  ms api-module list <projectId>
  ms functional-case list 登录
  ms functional-case-review list '{"projectId":"<project-id>","caseId":"<case-id>"}'
  ms case-review list '{"projectId":"<project-id>"}'
  ms case-review-detail list '{"projectId":"<project-id>","reviewId":"<review-id>"}'
  ms api list '{"projectId":"<project-id>","protocol":"HTTP"}'
"""
    )


def print_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def list_workspace(config: ms_client.MeterSphereConfig) -> None:
    print_json(ms_client.request_json(config, "GET", ms_client.resource_paths("workspace")["list"]))


def list_project(config: ms_client.MeterSphereConfig, arg: str) -> None:
    if arg == "all":
        path = ms_client.project_list_path("")
    else:
        workspace_id = arg or config.workspace_id
        path = ms_client.project_list_path(workspace_id)
    print_json(ms_client.request_json(config, "GET", path))


def list_functional_module(config: ms_client.MeterSphereConfig, arg: str) -> None:
    project_id = ms_client.ensure_project_id(config, arg or None)
    print_json(ms_client.request_json(config, "GET", ms_client.functional_module_path(project_id)))


def list_functional_template(config: ms_client.MeterSphereConfig, arg: str) -> None:
    project_id = ms_client.ensure_project_id(config, arg or None)
    print_json(ms_client.request_json(config, "GET", ms_client.functional_template_path(project_id)))


def list_api_module(config: ms_client.MeterSphereConfig, arg: str) -> None:
    project_id = ms_client.ensure_project_id(config, arg or None)
    print_json(ms_client.request_json(config, "GET", ms_client.api_module_path(project_id, config.protocol)))


def list_case_review_module(config: ms_client.MeterSphereConfig, arg: str) -> None:
    project_id = ms_client.ensure_project_id(config, arg or None)
    payload = {"projectId": project_id}
    print_json(
        ms_client.request_json(
            config,
            "POST",
            ms_client.resource_paths("case-review-module")["list"].replace("{projectId}", project_id),
            payload,
        )
    )


def list_case_review_user(config: ms_client.MeterSphereConfig, arg: str) -> None:
    project_id = ms_client.ensure_project_id(config, arg or None)
    print_json(
        ms_client.request_json(
            config,
            "GET",
            ms_client.resource_paths("case-review-user")["list"].replace("{projectId}", project_id),
        )
    )


def list_functional_case_review(config: ms_client.MeterSphereConfig, arg: str) -> None:
    from skills.scripts import ms_review_summary

    if arg.startswith("{"):
        body = ms_client.normalize_body("functional-case-review", arg, config)
    elif arg:
        body = {"caseId": arg}
    else:
        body = {"projectId": config.project_id} if config.project_id else {}

    project_id = body.get("projectId") or config.project_id
    review_id = body.get("reviewId")
    case_id = body.get("caseId") or body.get("id")

    if review_id:
        if not project_id:
            ms_client.die("functional-case-review 按 reviewId 查询时需要 projectId")
        items = ms_review_summary.fetch_review_case_items(project_id, review_id)
        print_json(ms_client.enrich_review_entries(config, items))
        return

    if case_id:
        if not project_id:
            ms_client.die("functional-case-review 按 caseId 查询时需要 projectId")
        print_json(ms_review_summary.fetch_case_reviews(project_id, case_id))
        return

    if not project_id:
        ms_client.die("functional-case-review 需要 projectId 或 caseId")
    print_json(ms_review_summary.fetch_all_case_review_entries(project_id))


def list_generic(config: ms_client.MeterSphereConfig, resource: str, arg: str) -> None:
    normalized = ms_client.normalize_resource(resource)
    if normalized == "workspace":
        list_workspace(config)
        return
    if normalized == "project":
        list_project(config, arg)
        return
    if normalized == "functional-module":
        list_functional_module(config, arg)
        return
    if normalized == "functional-template":
        list_functional_template(config, arg)
        return
    if normalized == "api-module":
        list_api_module(config, arg)
        return
    if normalized == "case-review-module":
        list_case_review_module(config, arg)
        return
    if normalized == "case-review-user":
        list_case_review_user(config, arg)
        return
    if normalized == "functional-case-review":
        list_functional_case_review(config, arg)
        return

    paths = ms_client.resource_paths(normalized)
    if arg.startswith("{"):
        body = ms_client.normalize_body(normalized, arg, config)
    else:
        body = ms_client.build_default_query_payload(normalized, arg, config)
    items = ms_client.paginated_post(config, paths["list"], body, page_size=config.page_size)
    print_json(items)


def get_generic(config: ms_client.MeterSphereConfig, resource: str, identifier: str) -> None:
    if not identifier:
        ms_client.die("get 需要 id")
    path = ms_client.resource_paths(resource)["get"]
    if not path:
        ms_client.die(f"资源 {resource} 不支持 get")
    print_json(ms_client.request_json(config, "GET", ms_client.replace_first_placeholder(path, identifier)))


def create_generic(config: ms_client.MeterSphereConfig, resource: str, raw_body: str) -> None:
    if not raw_body:
        ms_client.die("create 需要 JSON body")
    body = ms_client.normalize_body(resource, raw_body, config)
    multipart = ms_client.get_create_multipart_config(resource)
    response = ms_client.multipart_request(
        config,
        "POST",
        ms_client.resource_paths(resource)["create"],
        body,
        request_field_name=multipart["field_name"],
        files_field_name=multipart["files_field"],
        files=[],
    )
    print_json(response)


def main() -> None:
    config = ms_client.get_config()
    if len(sys.argv) < 2:
        usage()
        raise SystemExit(1)

    command = sys.argv[1]
    if command in {"help", "-h", "--help"}:
        usage()
        return

    if command == "raw":
        if len(sys.argv) < 4:
            ms_client.die("raw 需要 METHOD 和 PATH")
        method = sys.argv[2]
        path = sys.argv[3]
        body = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        print_json(ms_client.request_json(config, method, path, body))
        return

    if command == "reviewed-summary":
        from skills.scripts import ms_review_summary

        project_id = sys.argv[2] if len(sys.argv) > 2 else config.project_id
        keyword = sys.argv[3] if len(sys.argv) > 3 else ""
        if not project_id:
            ms_client.die("reviewed-summary 需要 projectId")
        print_json(ms_review_summary.build_summary_report(project_id, keyword))
        return

    if command == "case-report":
        from skills.scripts import ms_case_report

        if len(sys.argv) != 4:
            ms_client.die("用法: ms case-report <projectId> <caseId>")
        print_json(ms_case_report.build_case_report(sys.argv[2], sys.argv[3]))
        return

    if command == "case-report-md":
        from skills.scripts import ms_case_report
        from skills.scripts import ms_case_report_md

        if len(sys.argv) != 4:
            ms_client.die("用法: ms case-report-md <projectId> <caseId>")
        report = ms_case_report.build_case_report(sys.argv[2], sys.argv[3])
        print(ms_case_report_md.md_lines(report))
        return

    resource = command
    if len(sys.argv) < 3:
        ms_client.die("缺少 action")
    action = sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 else ""

    normalized = ms_client.normalize_resource(resource)
    ms_client.resource_paths(normalized)

    if action == "list":
        list_generic(config, normalized, arg)
    elif action == "get":
        get_generic(config, normalized, arg)
    elif action == "create":
        create_generic(config, normalized, arg)
    else:
        ms_client.die(f"不支持的 action: {action}")


if __name__ == "__main__":
    main()
