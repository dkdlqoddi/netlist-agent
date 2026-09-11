#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/dkdlqoddi/netlist-agent"
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "=== 1. Checking git submodule status ==="
[[ ! -f "$ROOT/.gitmodules" ]] || fail ".gitmodules exists (should not be submodule)"
git -C "$ROOT" submodule status 2>&1 | grep -q . && fail "submodule detected in git"
echo "PASS: No submodules configured"

echo "=== 2. Checking directory structure & count ==="
skills=("$ROOT"/.agents/skills/*/SKILL.md)
agents=("$ROOT"/.agents/agents/*.md)
rules=("$ROOT"/.agents/rules/*.md)

[[ ${#skills[@]} -eq 8 ]] || fail "expected 8 skills, got ${#skills[@]}"
[[ ${#agents[@]} -eq 11 ]] || fail "expected 11 agents, got ${#agents[@]}"
[[ ${#rules[@]} -eq 1 ]] || fail "expected 1 rule, got ${#rules[@]}"
echo "PASS: 8 skills, 11 agents, 1 rule found"

echo "=== 3. Frontmatter lint ==="
for f in "${skills[@]}"; do
  [[ "$(head -n1 "$f")" == "---" ]] || fail "$f: missing frontmatter open"
  fm="$(awk '/^---$/{c++; next} c==1' "$f")"
  grep -q '^name:' <<<"$fm" || fail "$f: missing name"
  grep -q '^description:' <<<"$fm" || fail "$f: missing description"
done

for f in "${rules[@]}"; do
  [[ "$(head -n1 "$f")" == "---" ]] || fail "$f: missing frontmatter open"
  fm="$(awk '/^---$/{c++; next} c==1' "$f")"
  grep -q '^trigger:' <<<"$fm" || fail "$f: rule needs trigger:"
done

for f in "${agents[@]}"; do
  [[ "$(head -n1 "$f")" == "---" ]] || fail "$f: missing frontmatter open"
  fm="$(awk '/^---$/{c++; next} c==1' "$f")"
  grep -q '^name:' <<<"$fm" || fail "$f: missing name"
  grep -q '^description:' <<<"$fm" || fail "$f: missing description"
  for kv in 'subagent: true' 'mainAgent: false' 'model: flash' 'commandExecutionPolicy: auto'; do
    grep -qx "$kv" <<<"$fm" || fail "$f: needs '$kv'"
  done
  grep -qx 'tools:' <<<"$fm" || fail "$f: needs 'tools:'"
  tools="$(grep -o '^  - .*' <<<"$fm" | sed 's/  - //')"
  [[ -n "$tools" ]] || fail "$f: tools allowlist is empty"
  for t in $tools; do
    case " view_file run_command write_to_file replace_file_content find_by_name grep_search list_dir read_url_content search_web send_message " in
      *" $t "*) ;; *) fail "$f: unknown tool '$t'" ;;
    esac
  done
done
echo "PASS: Frontmatter lint passed for skills, rules, agents"

echo "=== 4. Reference integrity ==="
refs="$(grep -ho '`TypeName: [a-z-]*`' "$ROOT"/.agents/skills/*/SKILL.md | sed 's/.*`TypeName: \([a-z-]*\)`.*/\1/' | sort -u)"
[[ -n "$refs" ]] || fail "no TypeName references"
while read -r name; do
  [[ -f "$ROOT/.agents/agents/$name.md" ]] || fail "skills reference agent '$name' but .agents/agents/$name.md is missing"
done <<<"$refs"

for f in "$ROOT"/.agents/agents/*.md; do
  name="$(basename "$f" .md)"
  grep -q "\`TypeName: $name\`" "$ROOT"/.agents/skills/*/SKILL.md || fail "$name not referenced in SKILL.md"
  grep -q "\`$name\`" "$ROOT/MANDATE.md" || fail "$name not in MANDATE.md"
done
echo "PASS: Reference integrity confirmed"

echo "=== 5. Readability standards (25 어절) ==="
n="$(grep -l '25 어절' "$ROOT"/.agents/skills/*/SKILL.md | wc -l)"
[[ "$n" -eq 4 ]] || fail "expected 4 skills with '25 어절', got $n"
echo "PASS: Readability standard in 4 skills"

echo "=== 6. Script & template execution ==="
python3 "$ROOT/.agents/skills/work-report/scripts/docs_check.py" \
  "$ROOT/.agents/skills/work-report/templates/quiz.html" \
  "$ROOT/.agents/skills/blindspot-pass/templates/rules.md" \
  "$ROOT/.agents/skills/blindspot-pass/templates/map.md" \
  "$ROOT/.agents/skills/explainer/templates/spec.md" >/dev/null || fail "docs_check failed on templates"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

sw="$tmp/sw/docs/swarm"; mkdir -p "$sw/tasks" "$tmp/sw/src"; : > "$tmp/sw/src/a.py"; : > "$tmp/sw/src/b.py"
printf '# x 스웜 계획\n\n- 기준 커밋: abc1234\n- 대상 spec: docs/core/specs/x.md\n- 작업 노트: docs/notes/x.md\n- 동시 실행 상한: 8\n- 전체 검증: `true`\n\n## 목표\n\nx\n\n## 작업\n\n| id | 제목 | 역할 | 웨이브 | 선행 |\n|---|---|---|---|---|\n| T01 | a | 구현 | 1 | 없음 |\n| T02 | b | 테스트 | 2 | T01 |\n\n## 회차\n\n| 회차 | 날짜 | 범위 | 비고 |\n|---|---|---|---|\n| 1 | 2026-01-01 | 전체 | |\n' > "$sw/plan.md"
brief() { printf '# %s x\n\n- 역할: 구현\n- 웨이브: %s\n- 선행: %s\n- 소유 파일: %s\n\n## 목표\n\nx\n\n## 해야 할 일\n\n1. x\n\n## 협업 프로토콜\n\nx\n\n## 완료 조건\n\n- [ ] x\n\n## 검증\n\n`true`\n' "$1" "$2" "$3" "$4"; }
brief T01 1 없음 '`src/a.py`, `src/new.py` (신규)' > "$sw/tasks/T01.md"
brief T02 2 T01 '`src/b.py`' > "$sw/tasks/T02.md"
python3 "$ROOT/.agents/skills/swarm-plan/scripts/swarm_check.py" "$sw/plan.md" >/dev/null || fail "swarm_check failed on valid package"
echo "PASS: docs_check.py and swarm_check.py working properly"

echo "=== 7. MANDATE & Guideline files ==="
[[ "$(wc -l < "$ROOT/MANDATE.md")" -le 60 ]] || fail "MANDATE.md over 60 lines"
[[ -f "$ROOT/AGENTS.md" ]] || fail "AGENTS.md missing"
[[ -e "$ROOT/ANTIGRAVITY.md" ]] || fail "ANTIGRAVITY.md missing"
out="$(bash "$ROOT/.agents/hooks/mandate.sh")"
for skill in requirements-interview blindspot-pass explainer work-report blindspot-flow swarm-plan swarm-run swarm-review; do
  grep -q "$skill" <<<"$out" || fail "mandate hook missing $skill"
done
echo "PASS: MANDATE.md, AGENTS.md, ANTIGRAVITY.md, mandate hook verified"

echo "ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!"
