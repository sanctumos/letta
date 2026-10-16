"""Fail unless coverage of this branch's Letta diff is at least 90 percent.

Reads coverage json (pytest-cov) and `git diff -U0 <base> HEAD -- letta`.
A changed line counts only when coverage recorded it as a statement.
"""

import json
import os
import re
import subprocess
import sys


def changed_lines(base: str) -> dict[str, set[int]]:
    diff = subprocess.check_output(["git", "diff", "-U0", base, "HEAD", "--", "letta"], text=True)
    found: dict[str, set[int]] = {}
    current = None
    new_line = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            if current != "/dev/null":
                found.setdefault(current, set())
            else:
                current = None
            new_line = None
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            new_line = int(match.group(1)) if match else None
        elif current and new_line is not None and line.startswith("+") and not line.startswith("+++"):
            found[current].add(new_line)
            new_line += 1
        elif current and new_line is not None and not line.startswith("-"):
            new_line += 1
    return found


def main() -> int:
    base = os.environ.get("SANCTUM_GATE_BASE", "8265efa")
    report_path = os.environ.get("COVERAGE_JSON", "coverage.json")
    threshold = float(os.environ.get("SANCTUM_GATE_THRESHOLD", "90"))
    report = json.load(open(report_path))
    files = report["files"]
    by_suffix = {path.replace("\\", "/"): data for path, data in files.items()}

    def file_data(rel: str):
        if rel in by_suffix:
            return by_suffix[rel]
        matches = [data for path, data in by_suffix.items() if path.endswith("/" + rel) or path.endswith(rel)]
        return matches[0] if matches else None

    measured = 0
    hit = 0
    missing_preview = []
    for rel, lines in changed_lines(base).items():
        data = file_data(rel)
        if data is None:
            statements = set()
            executed = set()
        else:
            executed = set(data.get("executed_lines") or [])
            missing = set(data.get("missing_lines") or [])
            statements = executed | missing
        interesting = lines & statements
        measured += len(interesting)
        hit += len(interesting & executed)
        for number in sorted(interesting - executed)[:8]:
            missing_preview.append(f"{rel}:{number}")

    if measured == 0:
        print("No executable changed lines were measured. Coverage json does not overlap the diff.")
        return 1
    percent = 100.0 * hit / measured
    print(f"diff coverage {percent:.1f}% ({hit}/{measured} statements) threshold {threshold:.0f}%")
    if missing_preview:
        print("uncovered sample:")
        for row in missing_preview[:40]:
            print(" ", row)
    if percent + 1e-9 < threshold:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
