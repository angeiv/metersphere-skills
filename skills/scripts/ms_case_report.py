#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills.scripts import ms_client
from skills.scripts import ms_review_summary


def parse_steps(steps_value):
    if isinstance(steps_value, list):
        return steps_value
    if isinstance(steps_value, str) and steps_value:
        try:
            return json.loads(steps_value)
        except Exception:
            return []
    return []


def normalize_tags(raw_tags):
    if isinstance(raw_tags, list):
        return raw_tags
    if isinstance(raw_tags, str) and raw_tags:
        return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    return []


def build_summary(detail: dict, bugs: list[dict], reviews: list[dict]) -> dict:
    return {
        "caseId": detail.get("id"),
        "num": detail.get("num"),
        "name": detail.get("name"),
        "moduleId": detail.get("nodeId"),
        "moduleName": detail.get("nodePath"),
        "projectId": detail.get("projectId"),
        "versionId": detail.get("versionId"),
        "versionName": detail.get("versionName"),
        "stepModel": detail.get("stepModel"),
        "priority": detail.get("priority"),
        "reviewStatus": detail.get("reviewStatus"),
        "lastExecuteResult": detail.get("lastExecuteResult"),
        "bugCount": len(bugs),
        "caseReviewCount": len(reviews),
        "reviewed": bool(reviews),
    }


def build_case_report(project_id: str, case_id: str) -> dict:
    detail = ms_review_summary.fetch_case_detail(case_id)
    reviews = ms_review_summary.fetch_case_reviews(project_id, case_id)
    bugs = ms_review_summary.fetch_case_bugs(project_id, case_id, detail)

    result = {
        "summary": build_summary(detail, bugs, reviews),
        "detail": {
            "prerequisite": detail.get("prerequisite"),
            "description": detail.get("remark") or detail.get("description"),
            "stepDescription": detail.get("stepDescription"),
            "expectedResult": detail.get("expectedResult"),
            "steps": parse_steps(detail.get("steps")),
            "attachments": detail.get("updatedFileList") or detail.get("attachments") or [],
            "tags": normalize_tags(detail.get("tags")),
        },
        "bugs": [
            {
                "id": bug.get("id") or bug.get("issuesId"),
                "num": bug.get("num") or bug.get("customNum"),
                "name": bug.get("name") or bug.get("title"),
                "statusName": bug.get("statusName") or bug.get("status"),
                "handleUserName": bug.get("handleUserName") or bug.get("assigneeName"),
                "createUserName": bug.get("createUserName") or bug.get("creator"),
                "createTime": bug.get("createTime"),
            }
            for bug in bugs
        ],
        "reviews": reviews,
    }
    return result


def main() -> None:
    if len(sys.argv) != 3:
        ms_client.die("用法: ms_case_report.py <projectId> <caseId>")
    print(json.dumps(build_case_report(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
