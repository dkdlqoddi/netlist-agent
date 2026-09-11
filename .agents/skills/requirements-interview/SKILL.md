---
name: requirements-interview
description: Use when the user starts discussing a new feature, change request, or any task with unclear requirements — runs a structured Korean interview (one question at a time, architecture-changing questions first) grounded in the area's rules, map, and recorded decisions, then writes the confirmed requirements and decisions into the unit's Tier 3 spec.
---

# Requirements Interview

The user's first prompt is a lossy map of what they actually need. Recover the territory by interviewing before building.

## Workflow

0. **Locate the tiers.** Decide which area the request touches (paths the user names; the areas present as `docs/*/map.md`). Read that area's `docs/<area>/rules.md` and the 단위 table of `docs/<area>/map.md`. If the area has no `map.md`, tell the user (Korean) that the area is not bootstrapped and offer `blindspot-pass`; if they decline, continue on a live scan and write only the spec.

1. **Classify first.** Sort what you know into the four quadrants (in your head — the table is not written anywhere):
   - Known Knowns — explicitly stated in the request
   - Known Unknowns — questions you already know need answers
   - Unknown Knowns — preferences the user likely holds but hasn't said (naming, style, existing patterns)
   - Unknown Unknowns — territory nobody has looked at; note candidates, leave the digging to `blindspot-pass`

2. **Ground before asking.** Pick the unit(s) the request touches from the 단위 table and read their `docs/<area>/specs/<unit>.md` if they exist. Collect past decisions across the whole area without opening every spec: `grep -h '^| 20' docs/<area>/specs/*.md` returns the one-line 결정 기록 rows. Then spawn ONE `codebase-scanner` agent (`TypeName: codebase-scanner`) with lens `conventions`, the task description, the `rules.md` and `map.md` paths, and the 위치 globs of the touched units, so it reports only what the tiers do not already say. Questions that ignore the actual code waste the user's time. Skip the scanner only if the project has no code yet.

3. **Interview.** In Korean, ONE question per message, via `ask_question` (or chat message) with 2–4 concrete options where possible.
   - Write every question and option for someone who has never seen the code: unavoidable technical terms plain Korean first with the term in parentheses; code identifiers only after a plain description of what they do. One fact per sentence, ≤25 어절 each.
   - Order by architecture impact: answers that change the design come first.
   - Never re-ask what a `rules.md` row or a 결정 기록 row already answers — cite the row and move on.
   - Stop when remaining answers would no longer change what you'd build (typically 3–6 questions).
   - Keep every question, answer, and its architecture impact — they become 결정 기록 rows.

4. **Write into the spec.** Target `docs/<area>/specs/<unit>.md` of the primary unit — the unit whose 위치 covers most of the files the work will touch. A feature that adds a module is a new unit: add its row to the map's 단위 table with 상세 명세 `specs/<unit>.md`. When you create a spec for a unit whose 단위 row says 상세 명세 `없음`, replace that cell with `specs/<unit>.md` in the same edit. If the spec does not exist, create it from the `explainer` skill's `templates/spec.md` (`.agents/skills/explainer/templates/spec.md` in consumer projects) with every heading present and 상태 초안, then fill only your sections:
   - 요구사항 — numbered, each item citing the answer that confirmed it
   - 결정 기록 — one row per answered question, one line each: 날짜 | 결정 | 근거 (the user's answer) | 기각한 대안 | 사용자
   - 열린 질문 — remaining Known Unknowns, plus Unknown Unknown candidates with 해소 계획 "blindspot-pass에서 점검"
   - 목적과 배경 — a 2–3 sentence draft only if it is empty; explainer owns it
   An answer that binds the whole area (a convention, a prohibition) also becomes a 불변 규칙 row in `rules.md`. Never touch sections another skill owns; append rows at the end of tables. When a 결정 기록 row you write answers an existing 열린 질문 row, delete that row in the same edit.
   Write for a reader who has never seen the code: no arrow shorthand (A→B) or unexplained jargon; unavoidable technical terms plain Korean first with the term in parentheses; one fact per sentence, ≤25 어절 each — split long compound sentences. 근거 cells keep their technical form. Before saving, self-check every sentence in 요구사항 and every 결정 cell: could someone who has never seen code follow it, and is it one fact within 25 어절? Update 최종 갱신 on every file you edited.

5. **Verify.** Spawn `doc-verifier` (`TypeName: doc-verifier`) on the spec, naming the sections you filled (요구사항, 결정 기록, 열린 질문). Fix every reported issue, re-save. Then run `python3 .agents/skills/work-report/scripts/docs_check.py <spec path> <map.md path, when you edited the map>` (the `work-report` skill's `scripts/docs_check.py`) and fix every violation. Do not skip on PASS-looking drafts — verification is not optional.

6. **Hand off.** Tell the user (Korean): 다음 단계는 `blindspot-pass`로 Unknown Unknowns를 구체화하는 것.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- Never ask the user something answerable by reading the code — that is what the scanner run is for.
- One decision per question. Batched questions get half-answers.
- A question the user cannot parse gets a guessed answer; guessed answers become wrong requirements. Every question and every document sentence must survive the "reader has never seen the code" test.
- Clean vocabulary does not equal readable: a 40+ 어절 sentence with nested clauses locks out the same readers even with zero jargon — the one-fact / ≤25 어절 bar is part of the standard.
- A question the user answered in a past cycle wastes the budget twice — past decisions live in the 결정 기록 rows across the area's specs; grep them so the interview can cite instead of re-ask.
- Reading every spec in the area "to be safe" is the old pile under a new name — the 단위 table says which specs the task touches; the grep covers the rest.
