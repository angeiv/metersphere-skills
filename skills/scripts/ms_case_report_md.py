#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills.scripts import ms_case_report
from skills.scripts import ms_client


def md_lines(report: dict) -> str:
    summary = report["summary"]
    detail = report["detail"]
    bugs = report.get("bugs") or []
    reviews = report.get("reviews") or []
    steps = detail.get("steps") or []

    lines = [
        f"# 功能用例报告：{summary.get('name') or '-'}",
        "",
        "## 用例摘要",
        f"- 用例ID：`{summary.get('caseId')}`",
        f"- 编号：`{summary.get('num')}`",
        f"- 模块：{summary.get('moduleName') or summary.get('moduleId') or '-'}",
        f"- 优先级：{summary.get('priority') or '-'}",
        f"- 步骤模式：{summary.get('stepModel') or '-'}",
        f"- 评审状态：{summary.get('reviewStatus') or '-'}",
        f"- 最近执行结果：{summary.get('lastExecuteResult') or '-'}",
        f"- 是否被评审过：{'是' if summary.get('reviewed') else '否'}",
        f"- 关联缺陷数：{summary.get('bugCount', 0)}",
        f"- 关联评审数：{summary.get('caseReviewCount', 0)}",
        "",
    ]

    if detail.get("prerequisite"):
        lines.extend(["## 前置条件", str(detail["prerequisite"]), ""])

    if detail.get("description"):
        lines.extend(["## 备注", str(detail["description"]), ""])

    if steps:
        lines.append("## 步骤")
        for index, step in enumerate(steps, start=1):
            lines.append(f"### 步骤 {index}")
            lines.append(f"- 操作：{step.get('desc') or '-'}")
            lines.append(f"- 预期：{step.get('result') or '-'}")
        lines.append("")

    lines.append("## 缺陷")
    if bugs:
        for index, bug in enumerate(bugs, start=1):
            lines.append(f"### 缺陷 {index}")
            lines.append(f"- 缺陷ID：`{bug.get('id')}`")
            lines.append(f"- 编号：`{bug.get('num')}`")
            lines.append(f"- 标题：{bug.get('name') or '-'}")
            lines.append(f"- 状态：{bug.get('statusName') or '-'}")
            lines.append(f"- 处理人：{bug.get('handleUserName') or '-'}")
            lines.append(f"- 创建人：{bug.get('createUserName') or '-'}")
    else:
        lines.append("- 暂无已关联缺陷")
    lines.append("")

    lines.append("## 评审记录")
    if reviews:
        for index, review in enumerate(reviews, start=1):
            lines.append(f"### 评审 {index}")
            lines.append(f"- 评审ID：`{review.get('reviewId')}`")
            lines.append(f"- 评审名称：{review.get('reviewName') or '-'}")
            lines.append(f"- 评审单状态：{review.get('reviewStatus') or '-'}")
            lines.append(f"- 该用例评审状态：{review.get('caseReviewStatus') or '-'}")
    else:
        lines.append("- 暂无评审记录")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    if len(sys.argv) != 3:
        ms_client.die("用法: ms_case_report_md.py <projectId> <caseId>")
    report = ms_case_report.build_case_report(sys.argv[1], sys.argv[2])
    print(md_lines(report))


if __name__ == "__main__":
    main()
