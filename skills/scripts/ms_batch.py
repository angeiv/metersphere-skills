#!/usr/bin/env python3
import copy
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills.scripts import ms_client

FUNCTIONAL_CASE_CREATE_PATH = "/track/test/case/add"
API_DEFINITION_CREATE_PATH = "/api/api/definition/create"
API_TEST_CASE_CREATE_PATH = "/api/api/testcase/create"


def load_payload(file_path: str):
    if file_path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(file_path).read_text(encoding="utf-8"))


def ensure_version(config: ms_client.MeterSphereConfig, payload: dict) -> dict:
    payload = copy.deepcopy(payload)
    project_id = payload.get("projectId")
    if project_id and not payload.get("versionId"):
        payload["versionId"] = ms_client.resolve_default_version_id(config, project_id)
    return payload


def create_functional_cases(payloads: list[dict]) -> list[dict]:
    config = ms_client.get_config()
    results = []
    for payload in payloads:
        prepared = ensure_version(config, payload)
        results.append(
            ms_client.multipart_request(
                config,
                "POST",
                FUNCTIONAL_CASE_CREATE_PATH,
                prepared,
                request_field_name="request",
                files_field_name="file",
                files=[],
            )
        )
    return results


def create_api_definitions_and_cases(bundle: dict) -> list[dict]:
    config = ms_client.get_config()
    results = []
    definitions = bundle.get("definitions", [])
    case_groups = bundle.get("cases", [])
    for definition, case_list in zip(definitions, case_groups):
        prepared_definition = ensure_version(config, definition)
        definition_response = ms_client.multipart_request(
            config,
            "POST",
            API_DEFINITION_CREATE_PATH,
            prepared_definition,
            request_field_name="request",
            files_field_name="files",
            files=[],
        )
        data = ms_client.extract_data(definition_response)
        definition_id = data.get("id") if isinstance(data, dict) else None
        case_results = []
        for case_payload in case_list:
            prepared_case = ensure_version(config, case_payload)
            prepared_case["projectId"] = prepared_definition["projectId"]
            prepared_case["apiDefinitionId"] = definition_id or prepared_case.get("apiDefinitionId", "")
            case_results.append(
                ms_client.multipart_request(
                    config,
                    "POST",
                    API_TEST_CASE_CREATE_PATH,
                    prepared_case,
                    request_field_name="request",
                    files_field_name="files",
                    files=[],
                )
            )
        results.append({"definition": definition_response, "cases": case_results})
    return results


def main() -> None:
    if len(sys.argv) != 3:
        ms_client.die("用法: ms_batch.py functional-cases <json-file> | api-import <json-file>")
    mode, file_path = sys.argv[1], sys.argv[2]
    payload = load_payload(file_path)
    if mode == "functional-cases":
        print(json.dumps(create_functional_cases(payload), ensure_ascii=False, indent=2))
        return
    if mode == "api-import":
        print(json.dumps(create_api_definitions_and_cases(payload), ensure_ascii=False, indent=2))
        return
    ms_client.die("未知模式")


if __name__ == "__main__":
    main()
