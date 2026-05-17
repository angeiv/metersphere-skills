#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / ".env"


RESOURCE_PATHS = {
    "workspace": {
        "list": "/project/workspace/list/userworkspace",
        "get": "",
        "create": "",
    },
    "project": {
        "list": "/project/project/list/all",
        "get": "/project/project/get/{id}",
        "create": "",
    },
    "functional-module": {
        "list": "/track/case/node/list/{projectId}",
        "get": "",
        "create": "",
    },
    "functional-template": {
        "list": "/setting/project/field/template/case/option/{projectId}",
        "get": "",
        "create": "",
    },
    "api-module": {
        "list": "/api/api/module/list/{projectId}/{protocol}",
        "get": "",
        "create": "",
    },
    "functional-case": {
        "list": "/track/test/case/list/{goPage}/{pageSize}",
        "get": "/track/test/case/get/{testCaseId}",
        "create": "/track/test/case/add",
    },
    "functional-case-review": {
        "list": "/track/test/review/case/list/{goPage}/{pageSize}",
        "get": "",
        "create": "",
    },
    "case-review": {
        "list": "/track/test/case/review/list/{goPage}/{pageSize}",
        "get": "/track/test/case/review/get/{reviewId}",
        "create": "",
    },
    "case-review-detail": {
        "list": "/track/test/review/case/list/{goPage}/{pageSize}",
        "get": "",
        "create": "",
    },
    "case-review-module": {
        "list": "/track/case/review/node/list/{projectId}",
        "get": "",
        "create": "",
    },
    "case-review-user": {
        "list": "/track/user/project/member/{projectId}",
        "get": "",
        "create": "",
    },
    "api": {
        "list": "/api/api/definition/list/{goPage}/{pageSize}",
        "get": "/api/api/definition/get/{id}",
        "create": "/api/api/definition/create",
    },
    "api-case": {
        "list": "/api/api/testcase/list/{goPage}/{pageSize}",
        "get": "/api/api/testcase/get/{id}",
        "create": "/api/api/testcase/create",
    },
}


MULTIPART_RESOURCE_CONFIG = {
    "functional-case": {"field_name": "request", "files_field": "file"},
    "api": {"field_name": "request", "files_field": "files"},
    "api-case": {"field_name": "request", "files_field": "files"},
}


def load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class MeterSphereConfig:
    base_url: str
    access_key: str
    secret_key: str
    headers_json: str
    project_id: str
    workspace_id: str
    protocol: str
    page_size: int
    default_version_id: str


def get_config() -> MeterSphereConfig:
    load_env()
    protocol = os.environ.get("METERSPHERE_PROTOCOL", "").strip()
    if not protocol:
        protocols_json = os.environ.get("METERSPHERE_PROTOCOLS_JSON", "")
        if protocols_json:
            try:
                parsed = json.loads(protocols_json)
                if isinstance(parsed, list) and parsed:
                    protocol = str(parsed[0])
            except Exception:
                protocol = ""
    return MeterSphereConfig(
        base_url=os.environ.get("METERSPHERE_BASE_URL", "").rstrip("/"),
        access_key=os.environ.get("METERSPHERE_ACCESS_KEY", ""),
        secret_key=os.environ.get("METERSPHERE_SECRET_KEY", ""),
        headers_json=os.environ.get("METERSPHERE_HEADERS_JSON", ""),
        project_id=os.environ.get("METERSPHERE_PROJECT_ID", ""),
        workspace_id=os.environ.get("METERSPHERE_WORKSPACE_ID", ""),
        protocol=protocol or "HTTP",
        page_size=int(os.environ.get("METERSPHERE_PAGE_SIZE", "20")),
        default_version_id=os.environ.get("METERSPHERE_DEFAULT_VERSION_ID", ""),
    )


def die(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_resource(resource: str) -> str:
    return resource


def resource_paths(resource: str) -> dict[str, str]:
    normalized = normalize_resource(resource)
    if normalized not in RESOURCE_PATHS:
        die(f"不支持的资源: {resource}")
    return RESOURCE_PATHS[normalized]


def project_list_path(workspace_id: str) -> str:
    return f"/project/project/listAll/{workspace_id}" if workspace_id else "/project/project/list/all"


def api_module_path(project_id: str, protocol: str) -> str:
    return f"/api/api/module/list/{project_id}/{protocol}"


def functional_module_path(project_id: str) -> str:
    return f"/track/case/node/list/{project_id}"


def functional_template_path(project_id: str) -> str:
    return f"/setting/project/field/template/case/option/{project_id}"


def generate_signature(access_key: str, secret_key: str) -> str:
    plain = f"{access_key}|{uuid.uuid4()}|{int(time.time() * 1000)}"
    proc = subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-128-cbc",
            "-K",
            secret_key.encode("utf-8").hex(),
            "-iv",
            access_key.encode("utf-8").hex(),
            "-base64",
            "-A",
            "-nosalt",
        ],
        input=plain.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode("utf-8").strip()


def build_headers(
    config: MeterSphereConfig,
    *,
    content_type: str | None = "application/json",
    accept: str = "application/json",
) -> dict[str, str]:
    if not config.base_url:
        die("未设置 METERSPHERE_BASE_URL")
    if not config.access_key:
        die("未设置 METERSPHERE_ACCESS_KEY")
    if not config.secret_key:
        die("未设置 METERSPHERE_SECRET_KEY")

    headers = {
        "ACCEPT": accept,
        "Connection": "close",
        "accessKey": config.access_key,
        "signature": generate_signature(config.access_key, config.secret_key),
    }
    if content_type:
        headers["Content-Type"] = content_type
    if config.headers_json:
        headers.update(json.loads(config.headers_json))
    return headers


def join_url(config: MeterSphereConfig, path: str) -> str:
    return f"{config.base_url}{path}"


def extract_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def extract_items_and_total(payload: Any) -> tuple[list[Any], int]:
    data = extract_data(payload)
    if isinstance(data, list):
        return data, len(data)
    if not isinstance(data, dict):
        return [], 0
    items = data.get("list")
    if items is None:
        items = data.get("listObject")
    if items is None:
        items = data.get("rows")
    if items is None:
        items = []
    total = data.get("total")
    if total is None:
        total = data.get("itemCount")
    if total is None:
        total = len(items)
    return items, int(total)


def request_json(
    config: MeterSphereConfig,
    method: str,
    path: str,
    body: Any | None = None,
) -> Any:
    try:
        return _request_json(config, method, path, body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"HTTP {exc.code}: {detail}")
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        die(str(exc))


def request_json_soft(
    config: MeterSphereConfig,
    method: str,
    path: str,
    body: Any | None = None,
) -> Any | None:
    try:
        return _request_json(config, method, path, body)
    except Exception:
        return None


def _request_json(
    config: MeterSphereConfig,
    method: str,
    path: str,
    body: Any | None = None,
) -> Any:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        join_url(config, path),
        data=data,
        headers=build_headers(config),
        method=method.upper(),
    )
    with request.urlopen(req, timeout=60) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        text = response.read().decode(charset, errors="replace")
        return json.loads(text)


def multipart_request(
    config: MeterSphereConfig,
    method: str,
    path: str,
    request_body: dict[str, Any],
    *,
    request_field_name: str = "request",
    files_field_name: str = "files",
    files: list[dict[str, Any]] | None = None,
) -> Any:
    try:
        return _multipart_request(
            config,
            method,
            path,
            request_body,
            request_field_name=request_field_name,
            files_field_name=files_field_name,
            files=files,
        )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"HTTP {exc.code}: {detail}")
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        die(str(exc))


def _multipart_request(
    config: MeterSphereConfig,
    method: str,
    path: str,
    request_body: dict[str, Any],
    *,
    request_field_name: str = "request",
    files_field_name: str = "files",
    files: list[dict[str, Any]] | None = None,
) -> Any:
    boundary = f"----MeterSphereSkill{uuid.uuid4().hex}"
    body_parts: list[bytes] = []

    def add_line(value: str) -> None:
        body_parts.append(value.encode("utf-8"))

    add_line(f"--{boundary}\r\n")
    add_line(
        f'Content-Disposition: form-data; name="{request_field_name}"\r\n'
        "Content-Type: application/json; charset=utf-8\r\n\r\n"
    )
    add_line(json.dumps(request_body, ensure_ascii=False))
    add_line("\r\n")

    for file_item in files or []:
        filename = file_item.get("filename", "attachment.bin")
        content = file_item.get("content", b"")
        if isinstance(content, str):
            content = content.encode("utf-8")
        content_type = file_item.get("content_type", "application/octet-stream")
        add_line(f"--{boundary}\r\n")
        add_line(
            f'Content-Disposition: form-data; name="{files_field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        )
        body_parts.append(content)
        add_line("\r\n")

    add_line(f"--{boundary}--\r\n")
    raw_body = b"".join(body_parts)
    headers = build_headers(config, content_type=None)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    headers["Content-Length"] = str(len(raw_body))
    req = request.Request(
        join_url(config, path),
        data=raw_body,
        headers=headers,
        method=method.upper(),
    )
    with request.urlopen(req, timeout=60) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def paginated_post(
    config: MeterSphereConfig,
    path_template: str,
    body: dict[str, Any],
    *,
    page_size: int = 100,
) -> list[Any]:
    page = 1
    items: list[Any] = []
    while True:
        path = path_template.format(goPage=page, pageSize=page_size)
        response = request_json(config, "POST", path, body)
        batch, total = extract_items_and_total(response)
        if not batch:
            break
        items.extend(batch)
        if len(items) >= total or len(batch) < page_size:
            break
        page += 1
    return items


def build_default_query_payload(
    resource: str,
    keyword: str,
    config: MeterSphereConfig,
) -> dict[str, Any]:
    normalized = normalize_resource(resource)
    payload: dict[str, Any] = {}
    if config.project_id and normalized not in {"workspace", "project"}:
        payload["projectId"] = config.project_id
    if config.workspace_id and normalized in {"project"}:
        payload["workspaceId"] = config.workspace_id
    if keyword:
        payload["name"] = keyword
    if normalized in {"api", "api-case"}:
        payload["protocol"] = config.protocol
        if config.default_version_id:
            payload["versionId"] = config.default_version_id
    if normalized == "functional-case" and config.default_version_id:
        payload["versionId"] = config.default_version_id
    return payload


def normalize_body(
    resource: str,
    raw_body: str,
    config: MeterSphereConfig,
) -> dict[str, Any]:
    data = json.loads(raw_body)
    if not isinstance(data, dict):
        die("请求体必须是 JSON 对象")
    if "organizationId" in data:
        die("MeterSphere 2.x 使用 workspaceId，不支持 organizationId")
    if "keyword" in data and "name" not in data:
        data["name"] = data.pop("keyword")
    normalized = normalize_resource(resource)
    if normalized not in {"workspace", "project"} and config.project_id and not data.get("projectId"):
        data["projectId"] = config.project_id
    if normalized == "project" and config.workspace_id and not data.get("workspaceId"):
        data["workspaceId"] = config.workspace_id
    if normalized in {"api", "api-case"}:
        data.setdefault("protocol", config.protocol)
        if config.default_version_id:
            data.setdefault("versionId", config.default_version_id)
    elif normalized == "functional-case" and config.default_version_id:
        data.setdefault("versionId", config.default_version_id)
    return data


def first_placeholder_name(path: str) -> str | None:
    match = re.search(r"\{([^}]+)\}", path)
    if not match:
        return None
    return match.group(1)


def replace_first_placeholder(path: str, value: str) -> str:
    return re.sub(r"\{[^}]+\}", value, path, count=1)


def resolve_default_version_id(config: MeterSphereConfig, project_id: str) -> str:
    if config.default_version_id:
        return config.default_version_id

    version = _resolve_default_version_via_endpoint(config, project_id)
    if version:
        return version

    version = _resolve_default_version_via_existing_cases(config, project_id)
    if version:
        return version

    die(
        "无法解析默认版本 ID，请设置 METERSPHERE_DEFAULT_VERSION_ID "
        "或确认项目下已有可读取的功能/API 用例可回退出 versionId"
    )


def _resolve_default_version_via_endpoint(config: MeterSphereConfig, project_id: str) -> str:
    try:
        response = _request_json(config, "GET", f"/project/project/version/get-default-version/{project_id}")
    except Exception:
        return ""
    data = extract_data(response)
    if isinstance(data, str) and data:
        return data
    if data:
        return str(data)
    return ""


def _resolve_default_version_via_existing_cases(config: MeterSphereConfig, project_id: str) -> str:
    fallback_queries = [
        ("POST", "/track/test/case/list/1/1", {"projectId": project_id}),
        ("POST", "/api/api/testcase/list/1/1", {"projectId": project_id, "protocol": config.protocol}),
        ("POST", "/api/api/definition/list/1/1", {"projectId": project_id, "protocol": config.protocol}),
    ]
    for method, path, body in fallback_queries:
        try:
            response = _request_json(config, method, path, body)
        except Exception:
            continue
        items, _ = extract_items_and_total(response)
        if not items:
            continue
        version_id = items[0].get("versionId")
        if version_id:
            return str(version_id)
    return ""


def ensure_project_id(config: MeterSphereConfig, explicit_project_id: str | None = None) -> str:
    project_id = explicit_project_id or config.project_id
    if not project_id:
        die("需要 projectId，请通过命令参数或 METERSPHERE_PROJECT_ID 提供")
    return project_id


def get_create_multipart_config(resource: str) -> dict[str, str]:
    normalized = normalize_resource(resource)
    if normalized not in MULTIPART_RESOURCE_CONFIG:
        die(f"资源 {resource} 不支持 multipart create")
    return MULTIPART_RESOURCE_CONFIG[normalized]


def enrich_review_entries(
    config: MeterSphereConfig,
    review_case_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    review_cache: dict[str, dict[str, Any]] = {}
    for item in review_case_items:
        review_id = item.get("reviewId")
        if review_id and review_id not in review_cache:
            response = request_json(config, "GET", f"/track/test/case/review/get/{review_id}")
            detail = extract_data(response)
            review_cache[review_id] = detail if isinstance(detail, dict) else {}
        review = review_cache.get(review_id, {})
        enriched.append(
            {
                "reviewId": review_id,
                "reviewName": review.get("name"),
                "reviewStatus": review.get("status"),
                "reviewerName": item.get("reviewerName") or review.get("reviewerName"),
                "caseReviewStatus": item.get("reviewStatus") or item.get("status"),
                "caseId": item.get("caseId") or item.get("id"),
            }
        )
    return enriched
