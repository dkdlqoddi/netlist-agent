#!/usr/bin/env python3
"""Mechanical checks for blindspot deliverables (quiz + tier documents).

Usage: python3 docs_check.py <path> [<path> ...]

Dispatch by path shape:
  parent directory named 'specs' -> Tier 3 spec
  basename rules.md              -> Tier 1
  basename map.md                -> Tier 2
  basename spec.md               -> Tier 3 (the shipped template)
  *.html                         -> pre-merge quiz
  anything else                  -> no checks (notes etc.)

Checks:
  quiz   : every sentence in the 변경 요약 block and every QUESTIONS q/explain has
           at most 25 어절 (whitespace-separated words); every option has at most
           40 characters
  Tier 1 : at most 60 lines
  Tier 2 : at most 150 lines; a 상세 명세 cell naming specs/<x>.md (plain,
           backticked, or linked) must name a file that exists next to the
           map; every specs/*.md next to the map must be named by some
           단위 row
  Tier 3 : at most 200 lines; sentences under 목적과 배경 / 요구사항 / 동작 방식 /
           의도적 범위 제외 have at most 25 어절

Prints violations and exits 1; exits 0 when clean.
"""
import os
import re
import sys

MAX_EOJEOL = 25
MAX_OPTION_CHARS = 40
CAPS = {1: 60, 2: 150, 3: 200}
PROSE_SECTIONS = ("목적과 배경", "요구사항", "동작 방식", "의도적 범위 제외")

# ponytail: regex over the templates' fixed shapes and a rough [.?!]+space
# sentence split; a real markdown/Korean parser only if the shapes change or
# quoted-sentence merging becomes a recurring miss.


def sentences(text):
    for s in re.split(r"(?<=[.?!])\s+", text.strip()):
        s = s.strip()
        if s:
            yield s


def eojeol_count(sentence):
    return len([t for t in sentence.split() if any(c.isalnum() for c in t)])


def unescape_js(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


def strip_comments(text):
    return re.sub(r"\s+", " ", re.sub(r"<!--.*?-->", " ", text, flags=re.S))


def check_prose(text, where, violations):
    for s in sentences(text):
        n = eojeol_count(s)
        if n > MAX_EOJEOL:
            violations.append(f'{where}: sentence has {n} 어절 (max {MAX_EOJEOL}): "{s}"')


def check_quiz(src, violations):
    m = re.search(r'<div class="summary">(.*?)</div>', src, re.S)
    if m:
        text = re.sub(r"<[^>]+>", " ", re.sub(r"<!--.*?-->", " ", m.group(1), flags=re.S))
        check_prose(re.sub(r"\s+", " ", text), "변경 요약", violations)
    else:
        violations.append('summary block (<div class="summary">) not found')
    m = re.search(r"const QUESTIONS = \[(.*?)\];", src, re.S)
    if not m:
        violations.append("QUESTIONS array not found")
        return
    body = m.group(1)
    for i, q in enumerate(re.finditer(r'\bq\s*:\s*"((?:[^"\\]|\\.)*)"', body), 1):
        check_prose(unescape_js(q.group(1)), f"Q{i} question", violations)
    for i, opts in enumerate(re.finditer(r"\boptions\s*:\s*\[(.*?)\]", body, re.S), 1):
        for o in re.finditer(r'"((?:[^"\\]|\\.)*)"', opts.group(1)):
            text = unescape_js(o.group(1))
            if len(text) > MAX_OPTION_CHARS:
                violations.append(
                    f'Q{i} option has {len(text)} chars (max {MAX_OPTION_CHARS}): "{text}"'
                )
    for i, ex in enumerate(re.finditer(r'\bexplain\s*:\s*"((?:[^"\\]|\\.)*)"', body), 1):
        check_prose(unescape_js(ex.group(1)), f"Q{i} explain", violations)


def tier_of(path):
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if parent == "specs":
        return 3
    return {"rules.md": 1, "map.md": 2, "spec.md": 3}.get(os.path.basename(path))


def section(src, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", src, re.S | re.M)
    return m.group(1) if m else None


def table_rows(body):
    """Rows of the markdown tables in body, as lists of cell strings (separator rows skipped)."""
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells[0] or set(cells[0]) <= set("-: "):
            continue
        yield cells


def check_cap(src, tier, violations):
    n = len(src.splitlines())
    if n > CAPS[tier]:
        violations.append(f"Tier {tier} file has {n} lines (max {CAPS[tier]})")


def check_map(path, src, violations):
    check_cap(src, 2, violations)
    body = section(src, "단위")
    if body is None:
        violations.append("'## 단위' section not found")
        return
    here = os.path.dirname(os.path.abspath(path))
    listed = set()
    for cells in table_rows(body):
        if cells[0] == "단위" or len(cells) < 4:
            continue
        m = re.search(r"specs/[^\s`|)\]]+\.md", cells[3])
        if m:
            ref = m.group(0)
            target = os.path.normpath(os.path.join(here, ref))
            listed.add(target)
            if not os.path.isfile(target):
                violations.append(f"단위 '{cells[0]}': 상세 명세 {ref} does not exist")
    specs_dir = os.path.join(here, "specs")
    if os.path.isdir(specs_dir):
        for name in sorted(os.listdir(specs_dir)):
            target = os.path.normpath(os.path.join(specs_dir, name))
            if name.endswith(".md") and target not in listed:
                violations.append(f"specs/{name} is not listed in any 단위 row")


def check_spec(src, violations):
    check_cap(src, 3, violations)
    for heading in PROSE_SECTIONS:
        body = section(src, heading)
        if body is None:
            violations.append(f"'## {heading}' section not found")
            continue
        check_prose(strip_comments(body), heading, violations)


def check_file(path, violations):
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        violations.append(f"{path}: file not found")
        return
    found = []
    if path.endswith(".html"):
        check_quiz(src, found)
    else:
        tier = tier_of(path)
        if tier == 1:
            check_cap(src, 1, found)
        elif tier == 2:
            check_map(path, src, found)
        elif tier == 3:
            check_spec(src, found)
    violations.extend(f"{path}: {v}" for v in found)


def main(argv):
    if not argv:
        print("usage: docs_check.py <quiz.html|rules.md|map.md|specs/*.md> [...]", file=sys.stderr)
        return 2
    violations = []
    for path in argv:
        check_file(path, violations)
    if violations:
        for v in violations:
            print(v)
        print(f"{len(violations)} violation(s)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
