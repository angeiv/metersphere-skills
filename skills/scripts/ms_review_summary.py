#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
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

CASE_LIST_PATH = "/track/test/case/list/{goPage}/{pageSize}"
CASE_REVIEW_LIST_PATH = "/track/test/case/review/list/{goPage}/{pageSize}"
REVIEW_CASE_LIST_PATH = "/track/test/review/case/list/{goPage}/{pageSize}"
CASE_GET_PATH = "/track/test/case/get/{testCaseId}"
CASE_ISSUES_LIST_PATH = "/track/test/case/issues/list"

_CASE_REVIEW_INDEX_CACHE: dict[str, dict[str, list[dict]]] = {}
_CASE_REVIEW_ENTRIES_CACHE: dict[str, list[dict]] = {}


def reset_caches() -> None:
    _CASE_REVIEW_INDEX_CACHE.clear()
    _CASE_REVIEW_ENTRIES_CACHE.clear()


def fetch_all_functional_cases(project_id: str, keyword: str) -> list[dict]:
    config = ms_client.get_config()
    body = {"projectId": project_id}
    if keyword:
        body["name"] = keyword
    return ms_client.paginated_post(config, CASE_LIST_PATH, body, page_size=100)


def fetch_case_detail(case_id: str) -> dict:
    config = ms_client.get_config()
    response = ms_client.request_json(config, "GET", CASE_GET_PATH.replace("{testCaseId}", case_id))
    data = ms_client.extract_data(response)
    return data if isinstance(data, dict) else {}


def fetch_case_review_records(project_id: str) -> list[dict]:
    config = ms_client.get_config()
    body = {"projectId": project_id}
    return ms_client.paginated_post(config, CASE_REVIEW_LIST_PATH, body, page_size=100)


def fetch_review_case_items(project_id: str, review_id: str) -> list[dict]:
    config = ms_client.get_config()
    body = {"projectId": project_id, "reviewId": review_id}
    return ms_client.paginated_post(config, REVIEW_CASE_LIST_PATH, body, page_size=100)


def reviewer_names(review: dict, item: dict) -> str | None:
    if item.get("reviewerName"):
        return item.get("reviewerName")
    reviewers = review.get("reviewers")
    if not isinstance(reviewers, list):
        return None
    names = [reviewer.get("name") for reviewer in reviewers if isinstance(reviewer, dict) and reviewer.get("name")]
    return "、".join(names) if names else None


def build_review_entry(review: dict, item: dict) -> dict:
    return {
        "reviewId": review.get("id") or item.get("reviewId"),
        "reviewName": review.get("name"),
        "reviewStatus": review.get("status"),
        "reviewerName": reviewer_names(review, item),
        "caseReviewStatus": item.get("reviewStatus") or item.get("status"),
        "caseId": item.get("caseId") or item.get("id"),
        "caseName": item.get("name"),
        "reviewCreateTime": review.get("createTime"),
        "reviewEndTime": review.get("endTime"),
    }


def build_case_review_index(project_id: str) -> tuple[dict[str, list[dict]], list[dict]]:
    index: dict[str, list[dict]] = {}
    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for review in fetch_case_review_records(project_id):
        review_id = review.get("id")
        if not review_id:
            continue
        try:
            review_case_items = fetch_review_case_items(project_id, review_id)
        except SystemExit:
            continue
        for item in review_case_items:
            case_id = item.get("caseId") or item.get("id")
            if not case_id:
                continue
            unique_key = (review_id, case_id)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            entry = build_review_entry(review, item)
            index.setdefault(case_id, []).append(entry)
            entries.append(entry)

    for case_entries in index.values():
        case_entries.sort(key=lambda item: item.get("reviewCreateTime") or 0, reverse=True)
    entries.sort(
        key=lambda item: ((item.get("reviewCreateTime") or 0), str(item.get("reviewId") or ""), str(item.get("caseId") or "")),
        reverse=True,
    )
    return index, entries


def get_case_review_index(project_id: str) -> dict[str, list[dict]]:
    cached = _CASE_REVIEW_INDEX_CACHE.get(project_id)
    if cached is None:
        cached, entries = build_case_review_index(project_id)
        _CASE_REVIEW_INDEX_CACHE[project_id] = cached
        _CASE_REVIEW_ENTRIES_CACHE[project_id] = entries
    return cached


def fetch_all_case_review_entries(project_id: str) -> list[dict]:
    get_case_review_index(project_id)
    return list(_CASE_REVIEW_ENTRIES_CACHE.get(project_id, []))


def fetch_case_reviews(project_id: str, case_id: str) -> list[dict]:
    return list(get_case_review_index(project_id).get(case_id, []))


def fetch_case_bugs(project_id: str, case_id: str, detail: dict | None = None) -> list[dict]:
    config = ms_client.get_config()
    response = ms_client.request_json_soft(
        config,
        "POST",
        CASE_ISSUES_LIST_PATH,
        {"projectId": project_id, "caseId": case_id},
    )
    if response is not None:
        data = ms_client.extract_data(response)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("list"), list):
            return data["list"]

    case_detail = detail if isinstance(detail, dict) else fetch_case_detail(case_id)
    issue_list = case_detail.get("issueList")
    return issue_list if isinstance(issue_list, list) else []


def build_case_summary(project_id: str, case_row: dict) -> dict:
    case_id = case_row.get("id")
    reviews = fetch_case_reviews(project_id, case_id)
    issue_list = case_row.get("issueList")
    bugs = issue_list if isinstance(issue_list, list) else []
    review_status = case_row.get("reviewStatus")
    reviewed = bool(reviews) or review_status not in {None, "", "Prepare"}
    return {
        "caseId": case_id,
        "num": case_row.get("num"),
        "name": case_row.get("name"),
        "priority": case_row.get("priority"),
        "stepModel": case_row.get("stepModel"),
        "reviewStatus": review_status,
        "bugCount": len(bugs),
        "reviewCount": len(reviews),
        "reviewed": reviewed,
        "reviews": reviews,
    }


def build_summary_report(project_id: str, keyword: str) -> dict:
    rows = fetch_all_functional_cases(project_id, keyword)
    get_case_review_index(project_id)
    summaries = [build_case_summary(project_id, row) for row in rows]
    return {
        "projectId": project_id,
        "keyword": keyword,
        "totalCases": len(summaries),
        "reviewedCases": sum(1 for item in summaries if item["reviewed"]),
        "unreviewedCases": sum(1 for item in summaries if not item["reviewed"]),
        "totalBugLinks": sum(item["bugCount"] for item in summaries),
        "list": summaries,
    }


def main() -> None:
    if len(sys.argv) < 2:
        ms_client.die("用法: ms_review_summary.py <projectId> [keyword]")
    project_id = sys.argv[1]
    keyword = sys.argv[2] if len(sys.argv) > 2 else ""
    print(json.dumps(build_summary_report(project_id, keyword), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
