---
name: explainer
description: Use when the user asks for a spec, design document, explainer, pitch, or "문서로 정리해줘" — completes the unit's Tier 3 spec (purpose, behavior, alternatives with trade-offs, explicit out-of-scope items) from the recorded requirements, decisions, and code reality, and updates the area map, so a zero-context reader can understand what is being built and why.
---

# Explainer

One spec a zero-context reader can use to understand what a unit does, what was decided, and what was deliberately left out.

## Workflow

1. **Gather inputs.** Read `docs/<area>/rules.md`, `docs/<area>/map.md`, and `docs/<area>/specs/<unit>.md` for every unit the topic touches; skim the code their 위치 columns name. If the touched spec has neither 요구사항 nor 결정 기록 rows, tell the user and recommend `requirements-interview` or `blindspot-pass` first — never fabricate requirements. Create a spec from `templates/spec.md` in this skill's folder only when the user explicitly says there is nothing to interview. If the area has no `map.md`, offer `blindspot-pass` (Korean); if the user declines, skip every map edit below and pass only the spec to `docs_check.py`.

2. **Write your sections.** You own 목적과 배경, 동작 방식, and 의도적 범위 제외 — rewrite them freely, but keep the as-built corrections and additions work-report appended to 동작 방식 and 의도적 범위 제외 (fold them into your prose; never drop them). In 결정 기록, fill empty 기각한 대안 cells and append new rows (one line each, date first); never edit rows other skills wrote. In 열린 질문, give every row a 해소 계획 or an owner. Do not touch 요구사항. Then update `map.md`: the unit's 단위 row (add it with 상세 명세 `specs/<unit>.md` when the unit is new) and a 주요 흐름 row for the behavior you described; append at the end of tables.
   The non-developer sections (목적과 배경, 동작 방식, 의도적 범위 제외) are for a reader who has never seen the code:
   - Describe what happens and why, never how the code looks. No arrow shorthand (A→B), no unexplained jargon; unavoidable technical terms plain Korean first with the term in parentheses — e.g. "설정 파일이 깨져 있으면(잘못된 JSON)".
   - One fact per sentence, ≤25 어절 each — split long compound sentences. Name concrete actors and actions ("사용자가 저장을 누르면"); on first appearance of an abstract concept, add one everyday example or comparison.
   - Code identifiers and file paths appear only where they are the subject being explained, introduced by a plain description.
   - Before saving, self-check every sentence: could someone who has never seen code follow it, and is it one fact within 25 어절? If not, rewrite it.

   The rules that matter most:
   - every real decision in 결정 기록 shows at least one rejected alternative and why
   - 의도적 범위 제외 — mandatory and never empty; if truly nothing was cut, state why the scope is total
   - 열린 질문 — each unresolved item gets an owner or a resolution plan

3. **Save** in place: set 상태 to 확정 and 최종 갱신 to today on the spec; update 최종 갱신 on the map.

4. **Verify.** Spawn IN PARALLEL (one message, two `invoke_subagent` entries): `doc-verifier` (`TypeName: doc-verifier`) on the spec naming the sections you filled, and `codebase-scanner` (`TypeName: codebase-scanner`) with lens `integration-points`, the spec and map paths, and instructions to cross-check them against code reality — every integration point the spec assumes, every 통합 지점 row, and every 위치 glob of the touched units must exist and match, mismatches cited as `file:line`. Fix every issue from both (correct map rows too), re-save. Then run `python3 .agents/skills/work-report/scripts/docs_check.py <spec> <map>` (the `work-report` skill's `scripts/docs_check.py`) and fix every violation. Skip the cross-check only when the project has no code.

5. **Hand off.** Tell the user (Korean): 구현 시작 시 `work-report` 노트 모드로.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- A spec is not a concatenation of interview answers and scan output; its 목적과 배경 and 동작 방식 must stand alone for a reader with zero context.
- A spec that reads like an engineering changelog fails its zero-context purpose; every sentence in the non-developer sections must survive the "reader has never seen the code" test.
- Clean vocabulary does not equal readable: a 40+ 어절 sentence with nested clauses locks out the same readers even with zero jargon — the one-fact / ≤25 어절 bar is part of the standard.
- Rewriting 요구사항 or another skill's 결정 기록 rows "for consistency" destroys the record the never-re-ask rule depends on — append, never rewrite.
- A spec created without an interview is fiction with headings; refuse unless the user says there is nothing to ask.
