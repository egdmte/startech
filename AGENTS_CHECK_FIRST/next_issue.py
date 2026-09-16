#!/usr/bin/env python3
"""
next_issue.py - Issue dispatcher for the student autonomous-car project.

Usage
-----
    python next_issue.py              # print next unresolved issue and exit
    python next_issue.py --done ID   # mark issue ID as resolved, then print next
    python next_issue.py --skip ID   # mark issue ID as skipped (re-queued last)
    python next_issue.py --list      # print all issues with current status
    python next_issue.py --reset     # clear all resolved/skipped marks

Agent workflow
--------------
1. Run this script once to receive the current issue.
2. Work on it.
3. Run again with --done <ID> to mark it resolved and receive the next one.

The script exits with code 0 on success so LLM runners can detect clean
completion without parsing stdout.  All readable output goes to stdout.
A single-line JSON summary is printed last so a piped agent can parse it.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent

LEGACY_AUDIT  = HERE / "LEGACY_audit.json"
CROSSCHECK    = HERE / "HATA_DEFTERI_crosscheck.json"
PROGRESS_FILE = HERE / "issue_progress.json"


def load_progress() -> dict[str, Any]:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"resolved": {}, "skipped": []}


def save_progress(progress: dict[str, Any]) -> None:
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def load_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if LEGACY_AUDIT.exists():
        with open(LEGACY_AUDIT, encoding="utf-8") as f:
            data = json.load(f)
        severity_rank = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}
        for item in data.get("issues", []):
            item_id = item.get("id") or item.get("reviewer_id") or f"F{item.get('line_start','?')}"
            issues.append({
                "id":            item_id,
                "source":        "LEGACY_audit",
                "title":         item.get("title", "(no title)"),
                "severity":      item.get("severity", "Unknown"),
                "severity_rank": severity_rank.get(item.get("severity", ""), 99),
                "file":          item.get("file", ""),
                "path":          item.get("path", ""),
                "line_start":    item.get("line_start"),
                "line_end":      item.get("line_end"),
                "status":        item.get("status", ""),
                "problem":       item.get("problem", ""),
                "fix":           item.get("fix", ""),
                "verification":  item.get("verification", ""),
                "trigger":       item.get("trigger", ""),
                "source_url":    item.get("source_url", ""),
                "related_locations": item.get("related_locations", []),
            })
    else:
        print(f"[WARN] {LEGACY_AUDIT.name} not found -- skipping.", file=sys.stderr)

    if CROSSCHECK.exists():
        with open(CROSSCHECK, encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("defects", []):
            raw_status = item.get("status", "")
            already_resolved = raw_status.lower().startswith("original defect resolved")
            issues.append({
                "id":            f"CHK-{item.get('handbook_id', '?')}",
                "source":        "HATA_DEFTERI_crosscheck",
                "title":         item.get("title", "(no title)"),
                "severity":      "Crosscheck",
                "severity_rank": 50 if not already_resolved else 99,
                "file":          "",
                "path":          "",
                "line_start":    None,
                "line_end":      None,
                "status":        raw_status,
                "problem":       item.get("verdict", ""),
                "fix":           item.get("recommended_action", ""),
                "verification":  item.get("remaining_risk_or_limit", ""),
                "trigger":       "",
                "source_url":    "",
                "related_locations": [],
                "_already_resolved": already_resolved,
            })
    else:
        print(f"[WARN] {CROSSCHECK.name} not found -- skipping.", file=sys.stderr)

    issues.sort(key=lambda x: x["severity_rank"])
    return issues


SEP = "=" * 72


def _wrap(text: str, width: int = 68, indent: str = "    ") -> str:
    lines = text.split("\n")
    wrapped = []
    for line in lines:
        wrapped.append(textwrap.fill(line, width=width,
                                     initial_indent=indent,
                                     subsequent_indent=indent))
    return "\n".join(wrapped)


def print_issue(issue: dict[str, Any], position: int, total: int) -> None:
    print(SEP)
    print(f"  ISSUE {position}/{total}  |  {issue['id']}  |  {issue['severity']}")
    print(SEP)
    print(f"  Title   : {issue['title']}")
    if issue.get("file"):
        loc = issue["file"]
        if issue.get("line_start"):
            loc += f"  lines {issue['line_start']}-{issue['line_end']}"
        print(f"  Location: {loc}")
    if issue.get("path"):
        print(f"  Path    : {issue['path']}")
    if issue.get("source_url"):
        print(f"  URL     : {issue['source_url']}")
    print()
    if issue.get("trigger"):
        print("  TRIGGER:")
        print(_wrap(issue["trigger"]))
        print()
    if issue.get("problem"):
        print("  PROBLEM:")
        print(_wrap(issue["problem"]))
        print()
    if issue.get("fix"):
        print("  RECOMMENDED FIX:")
        print(_wrap(issue["fix"]))
        print()
    if issue.get("verification"):
        print("  VERIFICATION / REMAINING RISK:")
        print(_wrap(issue["verification"]))
        print()
    if issue.get("related_locations"):
        print("  RELATED LOCATIONS:")
        for loc in issue["related_locations"]:
            print(f"    * {loc}")
        print()
    if issue.get("status"):
        print(f"  AUDIT STATUS: {issue['status']}")
        print()
    print(SEP)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the next unresolved issue from the audit JSON files.",
    )
    parser.add_argument("--done",  metavar="ID", help="Mark issue ID as resolved.")
    parser.add_argument("--skip",  metavar="ID", help="Move issue ID to end of queue.")
    parser.add_argument("--list",  action="store_true", help="List all issues with status.")
    parser.add_argument("--reset", action="store_true", help="Clear all resolved/skipped marks.")
    args = parser.parse_args()

    progress = load_progress()
    issues   = load_issues()

    if args.reset:
        progress = {"resolved": {}, "skipped": []}
        save_progress(progress)
        print("Progress reset. All issues are unresolved.")
        sys.exit(0)

    if args.done:
        iid = args.done.strip()
        if not any(x["id"] == iid for x in issues):
            print(f"[ERROR] No issue found with ID '{iid}'.", file=sys.stderr)
            sys.exit(1)
        progress["resolved"][iid] = datetime.now(timezone.utc).isoformat()
        if iid in progress.get("skipped", []):
            progress["skipped"].remove(iid)
        save_progress(progress)
        print(f"OK  Issue {iid} marked as resolved.\n")

    if args.skip:
        iid = args.skip.strip()
        if not any(x["id"] == iid for x in issues):
            print(f"[ERROR] No issue found with ID '{iid}'.", file=sys.stderr)
            sys.exit(1)
        skipped = progress.setdefault("skipped", [])
        if iid not in skipped:
            skipped.append(iid)
        save_progress(progress)
        print(f"SKIPPED  Issue {iid} moved to end of queue.\n")

    if args.list:
        resolved = progress.get("resolved", {})
        skipped  = progress.get("skipped", [])
        print(f"\n{'ID':<16} {'SEV':<12} {'STATUS':<28} TITLE")
        print("-" * 90)
        for issue in issues:
            iid = issue["id"]
            if iid in resolved:
                st = f"resolved ({resolved[iid][:10]})"
            elif issue.get("_already_resolved"):
                st = "resolved (source)"
            elif iid in skipped:
                st = "skipped"
            else:
                st = "open"
            print(f"{iid:<16} {issue['severity']:<12} {st:<28} {issue['title'][:40]}")
        print()
        sys.exit(0)

    resolved = progress.get("resolved", {})
    skipped  = progress.get("skipped", [])

    open_issues = [
        x for x in issues
        if x["id"] not in resolved
        and not x.get("_already_resolved")
        and x["id"] not in skipped
    ]
    skipped_issues = [
        x for x in issues
        if x["id"] in skipped
        and x["id"] not in resolved
        and not x.get("_already_resolved")
    ]
    queue = open_issues + skipped_issues

    if not queue:
        print(SEP)
        print("  ALL ISSUES RESOLVED -- nothing left in the queue.")
        print(SEP)
        summary = {
            "status":         "all_resolved",
            "resolved_count": len(resolved),
            "total_count":    len(issues),
        }
        print()
        print("JSON_SUMMARY:", json.dumps(summary))
        sys.exit(0)

    current    = queue[0]
    position   = len(resolved) + 1
    total_open = len(queue)
    total_all  = len(issues)

    print()
    print(f"  Resolved so far: {len(resolved)}  |  Remaining: {total_open}  |  Total: {total_all}")
    print()
    print_issue(current, position, total_all)

    summary = {
        "status":          "open",
        "id":              current["id"],
        "severity":        current["severity"],
        "title":           current["title"],
        "file":            current.get("file", ""),
        "line_start":      current.get("line_start"),
        "line_end":        current.get("line_end"),
        "source_url":      current.get("source_url", ""),
        "resolved_count":  len(resolved),
        "remaining_count": total_open,
        "total_count":     total_all,
    }
    print("JSON_SUMMARY:", json.dumps(summary, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
