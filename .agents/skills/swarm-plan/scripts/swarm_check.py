#!/usr/bin/env python3
"""Mechanical checks for a swarm plan package (docs/swarm/plan.md + tasks/<id>.md).

Usage: python3 swarm_check.py docs/swarm/plan.md

plan.md : header bullets 기준 커밋 / 전체 검증 (a backticked command) / 동시 실행 상한 (a number) /
          대상 spec / 작업 노트 present and not template guidance; sections 목표 / 작업 / 회차
          present; the 작업 table has at least one row of id | 제목 | 역할 | 웨이브 | 선행 with
          unique T01-style ids; every id has tasks/<id>.md and every tasks/*.md is listed
briefs  : header bullets 웨이브 / 선행 / 소유 파일 present and equal to the table; sections
          목표 / 해야 할 일 / 완료 조건 / 검증 present and non-empty; 선행 ids exist and sit in
          an earlier 웨이브; 소유 파일 paths exist unless marked (신규); no two tasks of one
          웨이브 own overlapping paths (a path is a directory when it ends with / or is one on
          disk); no delegating words (필요하면, 적절히)
both    : no template placeholders left ([제목], [주제], YYYY-MM-DD, TODO, TBD, <영역>, <단위>,
          <slug>, path/to/)

Prints violations and exits 1; exits 0 when clean.
"""
import glob
import os
import re
import sys
from fnmatch import fnmatch

PLACEHOLDERS = ("[제목]", "[주제]", "YYYY-MM-DD", "TODO", "TBD", "<영역>", "<단위>", "<slug>", "path/to/")
DELEGATING_WORDS = ("필요하면", "적절히")
PLAN_HEADER = ("기준 커밋", "전체 검증", "동시 실행 상한", "대상 spec", "작업 노트")
PLAN_SECTIONS = ("목표", "작업", "회차")
BRIEF_SECTIONS = ("목표", "해야 할 일", "협업 프로토콜", "완료 조건", "검증")
ID_RE = re.compile(r"^T\d{2,3}$")


def section(src, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", src, re.S | re.M)
    return m.group(1) if m else None


def bullet(src, label):
    m = re.search(rf"^- {re.escape(label)}:[ \t]*(.*?)[ \t]*$", src, re.M)
    return m.group(1) if m else None


def strip_comments(text):
    return re.sub(r"<!--.*?-->", " ", text, flags=re.S)


def table_rows(body):
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells[0] or set(cells[0]) <= set("-: "):
            continue
        yield cells


def deps(text):
    text = (text or "").strip()
    if not text or text == "없음":
        return []
    return [d.strip().strip("`") for d in text.split(",") if d.strip()]


def owned(text, root):
    """(normalized path, is_dir, is_new) triples from a 소유 파일 bullet."""
    out = []
    for m in re.finditer(r"`([^`]+)`(\s*\(신규\))?", text or ""):
        raw = m.group(1).strip()
        path = os.path.normpath(raw)
        is_dir = raw.endswith("/") or os.path.isdir(os.path.join(root, path))
        out.append((path, is_dir, bool(m.group(2))))
    return out


def overlaps(a, b):
    """a, b are (path, is_dir) pairs."""
    # ponytail: equality, fnmatch and directory-prefix on normalized paths; a real path-set intersection only if globs get fancy
    (pa, da), (pb, db) = a, b
    if pa == pb or fnmatch(pa, pb) or fnmatch(pb, pa):
        return True
    return (da and pb.startswith(pa + "/")) or (db and pa.startswith(pb + "/"))


def placeholders(text, where, violations):
    clean = strip_comments(text)
    for tok in PLACEHOLDERS:
        if tok in clean:
            violations.append(f"{where}: placeholder '{tok}' left in")


def header_value(src, label, where, violations):
    value = bullet(src, label)
    if not value:
        violations.append(f"{where}: header bullet '{label}' missing or empty")
        return None
    if value.lstrip("`").startswith("("):
        violations.append(f"{where}: header bullet '{label}' still holds template guidance: {value}")
        return None
    return value


def check_plan(plan, violations):
    src = open(plan, encoding="utf-8").read()
    values = {label: header_value(src, label, "plan.md", violations) for label in PLAN_HEADER}
    if values["전체 검증"] and not re.search(r"`[^`]+`", values["전체 검증"]):
        violations.append("plan.md: 전체 검증 must be a backticked command")
    if values["동시 실행 상한"] and not values["동시 실행 상한"].isdigit():
        violations.append("plan.md: 동시 실행 상한 must be a number")
    placeholders(src, "plan.md", violations)
    for h in PLAN_SECTIONS:
        if section(src, h) is None:
            violations.append(f"plan.md: '## {h}' section not found")
    body = section(src, "작업")
    if body is None:
        return {}
    table = {}
    for cells in table_rows(body):
        if cells[0] == "id":
            continue
        tid = cells[0].strip("`")
        if len(cells) < 5:
            violations.append(f"plan.md: row '{tid}' needs 5 cells (id | 제목 | 역할 | 웨이브 | 선행)")
            continue
        if not ID_RE.match(tid):
            violations.append(f"plan.md: id '{tid}' must look like T01")
        if tid in table:
            violations.append(f"plan.md: id '{tid}' listed twice")
        table[tid] = {"wave": cells[3], "deps": deps(cells[4])}
    if not table:
        violations.append("plan.md: 작업 table has no tasks")
    return table


def check_brief(tid, path, table, root, violations):
    src = open(path, encoding="utf-8").read()
    where = f"tasks/{tid}.md"
    placeholders(src, where, violations)
    wave = bullet(src, "웨이브")
    if not (wave and wave.isdigit()):
        violations.append(f"{where}: '- 웨이브: N' missing")
        wave = None
    elif wave != table[tid]["wave"]:
        violations.append(f"{where}: 웨이브 {wave} differs from plan.md ({table[tid]['wave']})")
    dep_line = bullet(src, "선행")
    if dep_line is None:
        violations.append(f"{where}: '- 선행:' missing (use 없음 when there is none)")
    elif deps(dep_line) != table[tid]["deps"]:
        violations.append(f"{where}: 선행 differs from plan.md")
    own = owned(bullet(src, "소유 파일"), root)
    if not own:
        violations.append(f"{where}: '- 소유 파일:' missing or names no backticked path")
    for p, _, is_new in own:
        full = os.path.join(root, p)
        if is_new:
            if os.path.exists(full):
                violations.append(f"{where}: '{p}' is marked (신규) but already exists")
        elif any(ch in p for ch in "*?["):
            if not glob.glob(full):
                violations.append(f"{where}: glob '{p}' matches nothing")
        elif not os.path.exists(full):
            violations.append(f"{where}: '{p}' does not exist (mark it (신규) if the worker creates it)")
    for h in BRIEF_SECTIONS:
        body = section(src, h)
        if body is None:
            violations.append(f"{where}: '## {h}' section not found")
            continue
        clean = strip_comments(body)
        if not clean.strip():
            violations.append(f"{where}: '## {h}' is empty")
        for word in DELEGATING_WORDS:
            if word in clean:
                violations.append(f"{where}: '## {h}' delegates a decision to the worker with '{word}' — decide it in the brief")
    return {"wave": int(wave) if wave else None, "own": [(p, d) for p, d, _ in own]}


def main(argv):
    if len(argv) != 1:
        print("usage: swarm_check.py docs/swarm/plan.md", file=sys.stderr)
        return 2
    plan = os.path.abspath(argv[0])
    if not os.path.isfile(plan):
        print(f"{argv[0]}: file not found")
        return 1
    swarm_dir = os.path.dirname(plan)
    root = os.path.abspath(os.path.join(swarm_dir, "..", ".."))
    tasks_dir = os.path.join(swarm_dir, "tasks")
    violations = []
    table = check_plan(plan, violations)
    brief_ids = {f[:-3] for f in os.listdir(tasks_dir) if f.endswith(".md")} if os.path.isdir(tasks_dir) else set()
    for tid in sorted(set(table) - brief_ids):
        violations.append(f"{tid}: listed in plan.md but tasks/{tid}.md is missing")
    for tid in sorted(brief_ids - set(table)):
        violations.append(f"tasks/{tid}.md: not listed in the plan.md 작업 table")
    briefs = {}
    for tid in sorted(set(table) & brief_ids):
        briefs[tid] = check_brief(tid, os.path.join(tasks_dir, tid + ".md"), table, root, violations)
    for tid, info in briefs.items():
        for dep in table[tid]["deps"]:
            if dep not in briefs:
                violations.append(f"{tid}: 선행 '{dep}' is not a task")
            elif info["wave"] is not None and briefs[dep]["wave"] is not None and briefs[dep]["wave"] >= info["wave"]:
                violations.append(f"{tid}: 선행 '{dep}' must sit in an earlier 웨이브")
    ids = sorted(briefs)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if briefs[a]["wave"] is None or briefs[a]["wave"] != briefs[b]["wave"]:
                continue
            for pa in briefs[a]["own"]:
                for pb in briefs[b]["own"]:
                    if overlaps(pa, pb):
                        violations.append(f"{a}/{b}: 소유 파일 overlap in 웨이브 {briefs[a]['wave']}: '{pa[0]}' vs '{pb[0]}'")
    if violations:
        for v in violations:
            print(v)
        print(f"{len(violations)} violation(s)")
        return 1
    print(f"OK — {len(briefs)} task(s), {len({b['wave'] for b in briefs.values()})} 웨이브")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
