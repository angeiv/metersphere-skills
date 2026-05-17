#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

try:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from skills.scripts import ms_client
except ModuleNotFoundError:
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))
    from scripts import ms_client

USAGE = """
用法:
  ms_generate.py functional-cases <projectId> <moduleId> <requirement-file>
  ms_generate.py api-import <projectId> <moduleId> <openapi-file-or-url>
"""


def load_text(path: str) -> str:
    candidate = Path(path)
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    if path.startswith(("http://", "https://")):
        with urllib.request.urlopen(path, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    return path


def split_requirement_items(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[\-\*\d\.\)\(\s]+", "", line).strip()
        if len(cleaned) >= 2:
            items.append(cleaned)
    if not items:
        items = [text.strip()]
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items[:50]


def infer_priority(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["登录", "支付", "权限", "下单", "critical", "login", "pay"]):
        return "P0"
    if any(token in lowered for token in ["查询", "搜索", "导出", "上传", "保存", "search", "query"]):
        return "P1"
    return "P2"


def infer_tags(text: str) -> str:
    mapping = {
        "登录": "登录",
        "注册": "注册",
        "支付": "支付",
        "权限": "权限",
        "查询": "查询",
        "搜索": "搜索",
        "导出": "导出",
        "导入": "导入",
        "上传": "上传",
        "下载": "下载",
        "api": "接口",
        "接口": "接口",
    }
    tags: list[str] = []
    for key, value in mapping.items():
        if key.lower() in text.lower() and value not in tags:
            tags.append(value)
    return ",".join(tags[:5])


def build_test_steps(requirement: str, variant_type: int) -> list[dict[str, str | int]]:
    if variant_type == 1:
        return [
            {"num": 1, "desc": "准备测试环境", "result": "环境准备就绪"},
            {"num": 2, "desc": f"执行{requirement}操作", "result": "操作执行成功"},
            {"num": 3, "desc": "验证业务结果", "result": "结果符合预期"},
        ]
    if variant_type == 2:
        return [
            {"num": 1, "desc": "准备测试环境", "result": "环境准备就绪"},
            {"num": 2, "desc": f"输入异常数据执行{requirement}", "result": "系统拦截异常输入"},
            {"num": 3, "desc": "验证错误提示", "result": "错误提示清晰明确"},
        ]
    return [
        {"num": 1, "desc": "准备测试环境", "result": "环境准备就绪"},
        {"num": 2, "desc": f"输入边界值执行{requirement}", "result": "系统正确处理边界值"},
        {"num": 3, "desc": "验证边界条件结果", "result": "边界条件下系统行为稳定"},
    ]


def build_prerequisite(requirement: str) -> str:
    if "登录" in requirement:
        return "用户已注册账号且系统正常运行"
    if "支付" in requirement or "下单" in requirement:
        return "用户已登录且账户余额充足"
    if "查询" in requirement or "搜索" in requirement:
        return "系统中存在相关数据"
    return "系统正常运行"


def build_case_variants(item: str) -> list[tuple[str, str]]:
    return [
        (f"{item}-主流程", "主流程"),
        (f"{item}-异常场景", "异常场景"),
        (f"{item}-边界场景", "边界场景"),
    ]


def resolve_version_for_draft(project_id: str) -> str:
    config = ms_client.get_config()
    if config.default_version_id:
        return config.default_version_id
    if config.base_url and config.access_key and config.secret_key:
        return ms_client.resolve_default_version_id(config, project_id)
    return ""


def build_functional_cases(project_id: str, module_id: str, text: str) -> list[dict]:
    version_id = resolve_version_for_draft(project_id)
    payloads: list[dict] = []
    for item in split_requirement_items(text):
        priority = infer_priority(item)
        tags = infer_tags(item)
        for index, (name, label) in enumerate(build_case_variants(item), start=1):
            payloads.append(
                {
                    "projectId": project_id,
                    "nodeId": module_id,
                    "name": name[:255],
                    "priority": priority,
                    "stepModel": "STEP",
                    "steps": json.dumps(build_test_steps(item, index), ensure_ascii=False),
                    "prerequisite": build_prerequisite(item),
                    "remark": f"根据需求自动生成的功能用例，类型={label}",
                    "versionId": version_id,
                    "tags": tags,
                    "customFields": "[]",
                }
            )
    return payloads[:120]


def parse_openapi_source(text: str):
    try:
        return json.loads(text)
    except Exception:
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text)
        except Exception as exc:
            raise RuntimeError("无法解析 OpenAPI/Swagger 文档，请提供 JSON 或 YAML") from exc


def sample_value(schema_type: str, name: str = ""):
    if schema_type == "integer":
        return "1"
    if schema_type == "number":
        return "1"
    if schema_type == "boolean":
        return "true"
    if "id" in name.lower():
        return "1001"
    return "test"


def json_example_from_schema(schema: dict):
    if not isinstance(schema, dict):
        return None
    if "example" in schema:
        return schema["example"]
    schema_type = schema.get("type")
    if schema_type == "object":
        result = {}
        for key, value in (schema.get("properties") or {}).items():
            example_value = json_example_from_schema(value)
            result[key] = example_value if example_value is not None else sample_value((value or {}).get("type", "string"), key)
        return result
    if schema_type == "array":
        item_value = json_example_from_schema(schema.get("items") or {})
        return [item_value] if item_value is not None else []
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1
    if schema_type == "boolean":
        return True
    return "test"


def build_assertions(expected_code: str = "200") -> list[dict]:
    return [
        {
            "enable": True,
            "name": "状态码断言",
            "assertionType": "RESPONSE_CODE",
            "condition": "EQUALS",
            "expectedValue": expected_code,
        }
    ]


def build_http_request(method: str, path: str, summary: str, operation: dict) -> dict:
    body_type = "NONE"
    json_value = ""
    if "requestBody" in operation:
        content = operation.get("requestBody", {}).get("content", {})
        if "application/json" in content:
            body_type = "JSON"
            schema = content["application/json"].get("schema") or {}
            example_value = content["application/json"].get("example")
            if example_value is None:
                examples = content["application/json"].get("examples") or {}
                if isinstance(examples, dict) and examples:
                    first = next(iter(examples.values()))
                    example_value = first.get("value") if isinstance(first, dict) else None
            if example_value is None:
                example_value = json_example_from_schema(schema)
            json_value = json.dumps(example_value if example_value is not None else {}, ensure_ascii=False, indent=2)
        elif "application/x-www-form-urlencoded" in content:
            body_type = "WWW_FORM"
        elif "multipart/form-data" in content:
            body_type = "FORM_DATA"
        else:
            body_type = "RAW"

    query = []
    rest = []
    headers = []
    for parameter in operation.get("parameters", []) or []:
        schema = parameter.get("schema") or {}
        value = parameter.get("example")
        if value is None:
            value = sample_value(schema.get("type", "string"), parameter.get("name", ""))
        entry = {
            "key": parameter.get("name", ""),
            "value": str(value),
            "enable": True,
            "description": parameter.get("description"),
            "paramType": schema.get("type", "string") or "string",
            "required": parameter.get("required", False),
            "minLength": None,
            "maxLength": None,
            "encode": False,
        }
        location = parameter.get("in")
        if location == "query":
            query.append(entry)
        elif location == "path":
            rest.append(entry)
        elif location == "header":
            headers.append(
                {
                    "key": entry["key"],
                    "value": entry["value"],
                    "enable": True,
                    "description": entry["description"],
                }
            )

    body = {
        "bodyType": body_type,
        "noneBody": {} if body_type == "NONE" else None,
        "formDataBody": {"formValues": []},
        "wwwFormBody": {"formValues": []},
        "jsonBody": {"enableJsonSchema": body_type == "JSON", "jsonValue": json_value, "jsonSchema": None},
        "xmlBody": {"value": ""},
        "rawBody": {"value": ""},
        "binaryBody": {"description": "", "file": None},
    }
    return {
        "polymorphicName": "MsHTTPElement",
        "stepId": "",
        "resourceId": "",
        "projectId": None,
        "name": summary or f"{method.upper()} {path}",
        "enable": True,
        "children": [
            {
                "polymorphicName": "MsCommonElement",
                "stepId": None,
                "resourceId": None,
                "projectId": None,
                "name": None,
                "enable": True,
                "children": [],
                "parent": None,
                "csvIds": None,
                "preProcessorConfig": {"enableGlobal": False, "processors": []},
                "postProcessorConfig": {"enableGlobal": False, "processors": []},
                "assertionConfig": {"enableGlobal": False, "assertions": build_assertions("200")},
            }
        ],
        "parent": None,
        "csvIds": None,
        "customizeRequest": False,
        "customizeRequestEnvEnable": False,
        "path": path,
        "method": method.upper(),
        "body": body,
        "headers": headers,
        "rest": rest,
        "query": query,
        "otherConfig": {
            "connectTimeout": 60000,
            "responseTimeout": 60000,
            "certificateAlias": "",
            "followRedirects": True,
            "autoRedirects": False,
        },
        "authConfig": {
            "authType": "NONE",
            "basicAuth": {"userName": "", "password": "", "valid": False},
            "digestAuth": {"userName": "", "password": "", "valid": False},
            "httpauthValid": False,
        },
        "moduleId": "",
        "num": None,
        "mockNum": None,
    }


def build_default_response() -> dict:
    return {
        "id": None,
        "statusCode": "200",
        "defaultFlag": True,
        "name": None,
        "headers": [],
        "body": {
            "bodyType": "JSON",
            "jsonBody": {
                "enableJsonSchema": False,
                "jsonValue": "{ }",
                "jsonSchema": {"type": "string", "properties": {}, "enable": True},
            },
            "xmlBody": {"value": None},
            "rawBody": {"value": None},
            "binaryBody": {"sendAsBody": False, "description": None, "file": None},
        },
    }


def set_assertion(request_obj: dict, expected_code: str) -> dict:
    request_copy = copy.deepcopy(request_obj)
    if request_copy.get("children"):
        request_copy["children"][0]["assertionConfig"] = {
            "enableGlobal": False,
            "assertions": build_assertions(expected_code),
        }
    return request_copy


def build_case_variants_for_api(summary: str, request_obj: dict, has_required: bool, has_params: bool, version_id: str) -> list[dict]:
    cases = []
    success_request = set_assertion(request_obj, "200")
    cases.append(
        {
            "projectId": "",
            "apiDefinitionId": "",
            "name": f"{summary[:180]}-成功场景",
            "priority": "P1",
            "status": "Underway",
            "versionId": version_id,
            "request": success_request,
            "description": "自动生成的成功场景用例",
            "response": json.dumps(build_default_response(), ensure_ascii=False),
            "tags": "接口,自动生成",
        }
    )
    if has_required:
        missing = copy.deepcopy(request_obj)
        for group in ["query", "rest"]:
            for item in missing.get(group, []):
                if item.get("required"):
                    item["value"] = ""
                    break
        missing = set_assertion(missing, "400")
        cases.append(
            {
                "projectId": "",
                "apiDefinitionId": "",
                "name": f"{summary[:180]}-必填缺失",
                "priority": "P1",
                "status": "Underway",
                "versionId": version_id,
                "request": missing,
                "description": "自动生成的必填缺失场景",
                "response": json.dumps(build_default_response(), ensure_ascii=False),
                "tags": "接口,自动生成",
            }
        )
    if has_params:
        edge = copy.deepcopy(request_obj)
        for group in ["query", "rest"]:
            for item in edge.get(group, []):
                if item.get("paramType") == "string":
                    item["value"] = "X" * 128
                    break
        edge = set_assertion(edge, "200")
        cases.append(
            {
                "projectId": "",
                "apiDefinitionId": "",
                "name": f"{summary[:180]}-边界场景",
                "priority": "P2",
                "status": "Underway",
                "versionId": version_id,
                "request": edge,
                "description": "自动生成的边界场景",
                "response": json.dumps(build_default_response(), ensure_ascii=False),
                "tags": "接口,自动生成",
            }
        )
    return cases


def build_openapi_import(project_id: str, module_id: str, text: str) -> dict:
    spec = parse_openapi_source(text)
    version_id = resolve_version_for_draft(project_id)
    definitions = []
    cases = []
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
            if method not in path_item:
                continue
            operation = path_item[method] or {}
            summary = operation.get("summary") or operation.get("operationId") or f"{method.upper()} {path}"
            request_obj = build_http_request(method, path, summary, operation)
            definition = {
                "projectId": project_id,
                "moduleId": module_id,
                "name": summary[:255],
                "protocol": "HTTP",
                "method": method.upper(),
                "path": path,
                "status": "Underway",
                "description": operation.get("description") or "",
                "request": request_obj,
                "response": json.dumps(build_default_response(), ensure_ascii=False),
                "versionId": version_id,
                "tags": "接口,自动生成",
            }
            definitions.append(definition)
            has_required = any(item.get("required") for item in request_obj.get("query", []) + request_obj.get("rest", []))
            has_params = bool(request_obj.get("query") or request_obj.get("rest"))
            case_list = build_case_variants_for_api(summary, request_obj, has_required, has_params, version_id)
            for case in case_list:
                case["projectId"] = project_id
            cases.append(case_list)
    return {"definitions": definitions, "cases": cases}


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        raise SystemExit(1)
    mode = sys.argv[1]
    if mode == "functional-cases":
        if len(sys.argv) != 5:
            print(USAGE, file=sys.stderr)
            raise SystemExit(1)
        project_id, module_id, requirement_file = sys.argv[2:5]
        text = load_text(requirement_file)
        print(json.dumps(build_functional_cases(project_id, module_id, text), ensure_ascii=False, indent=2))
        return
    if mode == "api-import":
        if len(sys.argv) != 5:
            print(USAGE, file=sys.stderr)
            raise SystemExit(1)
        project_id, module_id, source = sys.argv[2:5]
        text = load_text(source)
        print(json.dumps(build_openapi_import(project_id, module_id, text), ensure_ascii=False, indent=2))
        return
    print(USAGE, file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
