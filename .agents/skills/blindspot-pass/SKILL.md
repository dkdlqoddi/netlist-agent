---
name: blindspot-pass
description: Use when starting work in an unfamiliar codebase or domain, before writing an implementation plan, when the user asks what they might be missing ("내가 모르는 게 뭐지"), or when an area has no docs/<area>/map.md yet or the user asks to refresh the map — fans out parallel codebase-scanner agents (plus a domain-researcher for knowledge outside the codebase), converts unknown unknowns into concrete decidable questions, resolves them with the user, and files every finding into the area's rules, map, or unit spec.
---

# Blindspot Pass

Unknown unknowns are the failures you don't see coming. Concretize them into decidable questions before they become rework — and leave the tiers better than you found them.

## Workflow

0. **Bootstrap or refresh (only when needed).** Run this step when the touched area has no `docs/<area>/map.md`, or when the user asks for a map refresh with no feature attached.
   - Decide the areas from evidence. Existing `docs/*/map.md` win. Otherwise look at most two directory levels deep: a directory named `frontend`, `web`, `client`, `ui`, `app`, or `apps/*` holding a UI manifest (package.json depending on react, vue, svelte, next, nuxt, or angular; or index.html with src/) → `frontend`; a directory named `backend`, `server`, `api`, `service`, or `services/*`, or a server manifest (go.mod, pom.xml, build.gradle*, Cargo.toml, pyproject/requirements with django, fastapi, or flask, Gemfile, composer.json, *.csproj, mix.exs, package.json depending on express, fastify, nest, hono, or koa) → `backend`. Distinct matches → both areas; one match → that one; the same directory matching both, or nothing → one area named `core`. State the result in Korean. Ask ONE question (via `ask_question` or chat) with the candidates only when the evidence genuinely conflicts.
   - Spawn `codebase-scanner` agents IN PARALLEL (`TypeName: codebase-scanner`), per area, lenses `structure`, `conventions`, `integration-points`, `edge-cases` — each with the area root and this task's description, and the existing tier paths when refreshing. At most 8 agents per call; with more than two areas, bootstrap only the areas this task touches.
   - Create `docs/<area>/rules.md` and `docs/<area>/map.md` from `templates/rules.md` and `templates/map.md` in this skill's folder and fill them: structure → 단위 table with 상세 명세 `없음` on every row (never create specs here); conventions → 불변 규칙 and 관례; integration-points → 통합 지점; edge-cases → 알려진 위험 (only risks spanning two or more units); discovered test/lint/build commands → 표준 명령. A refresh edits rows in place. Write the decided code root into the 코드 루트 line of both files.
   - If this call is a bootstrap or refresh only (another skill's step 0, blindspot-flow stage 0, or a map refresh with no feature attached), stop here: run step 6 on the two files and hand off (Korean): 이제 `requirements-interview`부터. Otherwise carry these findings straight into step 3 and skip step 2's fan-out for the same task.

1. **Collect input and classify territory.** The task description, `docs/<area>/rules.md`, the 단위 table of `docs/<area>/map.md`, the specs of the units the task touches, and the area's decision rows (`grep -h '^| 20' docs/<area>/specs/*.md`) — do not re-ask what they already answer. Split the unfamiliarity into two territories: code (this repository) and domain (knowledge living outside the codebase — e.g. color grading, payment standards). A task can have both.

2. **Fan out scanners.** Spawn `codebase-scanner` agents IN PARALLEL (one message, multiple `invoke_subagent` entries, `TypeName: codebase-scanner`), one per lens:
   - `conventions`
   - `similar-features`
   - `integration-points`
   - `edge-cases`
   Each agent receives: its lens, the task description, the `rules.md` and `map.md` paths, the touched specs' paths, and the 위치 globs of the touched units — with the instruction to report only what those documents do not already state, cite any row it contradicts, and tag every finding with its 반영 계층. Use 3 lenses (drop `similar-features`) when the project is greenfield; skip the codebase lenses entirely only when the task touches no code.

   If domain territory exists, add ONE `domain-researcher` agent (`TypeName: domain-researcher`) to the same parallel batch, with: the domain topic, the task description, and what the user already knows (including the 용어 rows already in `rules.md`).

3. **Synthesize.** Merge findings yourself (plain reasoning, no extra agent). For each finding: restate it as a concrete, decidable question ("X를 어떻게 할지", not "X 주의") written for someone who has never seen the code — unavoidable technical terms plain Korean first with the term in parentheses, code identifiers only after a plain description, one fact per sentence, ≤25 어절 each. Assign a quadrant, sort by architecture impact. Keep evidence attached — `file:line` for code findings, source URL for domain findings; evidence stays technical.

4. **Resolve with the user.** Present questions in Korean via `ask_question` (or chat message), architecture-changing first. Questions, options, and the primer follow the same non-developer bar as step 3. If domain findings exist, open with a short primer (5–10 lines in Korean, from the researcher's 핵심 개념, short sentences with an everyday comparison for each abstract concept) — the user must understand the concepts to answer the questions. Questions the findings already answer: decide yourself and record them as 결정 기록 rows with 결정 주체 자체 and the evidence as 근거. If more than 7 questions remain after self-resolution, do not present them all — the count signals thin evidence, so spawn follow-up `codebase-scanner` / `domain-researcher` agents targeted at the weakest-evidence clusters and self-resolve again. Each follow-up agent receives the prior findings for its cluster so it extends, not repeats, the exploration. Present at most the 7 highest architecture-impact questions; move the rest to the spec's 열린 질문 with a 재방문 시점.

5. **File the findings.** There is no unknowns document — every finding goes to the tier where it will be read next, or is dropped:

   | Finding | Destination |
   |---|---|
   | convention, prohibition, area-wide invariant | `rules.md` 불변 규칙 / 관례 |
   | new or moved unit | `map.md` 단위 |
   | integration point | `map.md` 통합 지점 |
   | risk spanning two or more units | `map.md` 알려진 위험 |
   | single-unit failure mode or constraint | spec 엣지케이스와 제약 |
   | prior art from `similar-features` | cited in the 근거 cell of the decision it informs; a reuse rule → `rules.md` 관례 |
   | domain 핵심 개념 used by two or more units | `rules.md` 용어, with 출처 |
   | domain 품질 기준 | spec 요구사항 as acceptance criteria, with 출처 |
   | question resolved by the user or self-resolved | spec 결정 기록: 날짜 \| 결정 \| 근거 \| 기각한 대안 \| 사용자 or 자체 — one line per row |
   | question parked | spec 열린 질문 with 재방문 시점 |
   | fits nowhere | dropped — never archive raw scan output anywhere |

   A spec that does not exist yet is created from the `explainer` skill's `templates/spec.md` (`.agents/skills/explainer/templates/spec.md` in consumer projects) with every heading present and 상태 초안; fill only the sections above, and replace the unit's 상세 명세 cell in `map.md` (`없음`) with `specs/<unit>.md` in the same edit. Append rows at the end of tables; never rewrite rows other skills wrote. When a 결정 기록 row you write answers an existing 열린 질문 row, delete that row in the same edit. The 결정, 질문, and 규칙 cells are read by non-developers — apply the step 3 sentence bar to them; before saving, self-check every sentence in those cells: could someone who has never seen code follow it, and is it one fact within 25 어절? The 근거 cells are technical evidence for later stages — technical language is correct there; do not simplify it. Update 최종 갱신 on every file you edited.

6. **Verify.** For every file you edited, spawn `doc-verifier` (`TypeName: doc-verifier`) naming the sections you filled; fix every issue, re-save. Then run `python3 .agents/skills/work-report/scripts/docs_check.py <every edited file>` (the `work-report` skill's `scripts/docs_check.py`) and fix every violation — over the line cap means content sits at the wrong tier: move it down, never raise the cap.

7. **Hand off.** Tell the user (Korean): 설계 문서가 필요하면 `explainer`, 바로 구현이면 `work-report` 노트 모드로.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- Scanners return findings; YOU convert them to questions. A finding without a decision attached is noise.
- Do not serialize the scanner spawns — parallel or it takes 4x longer.
- Domain unknowns don't live in the repo — codebase lenses on a pure-domain task return empty findings. Classify territory first; route domain topics to `domain-researcher`.
- A concretized question the user cannot parse defeats the whole pass — the decision gets guessed, not made. Questions and decisions in plain Korean; 근거 cells stay technical, and there is no raw scan summary any more — a finding that files nowhere is dropped, not archived.
- Clean vocabulary does not equal readable: a 40+ 어절 sentence with nested clauses locks out the same readers even with zero jargon — the one-fact / ≤25 어절 bar is part of the standard.
- A long question list is an analysis failure, not thoroughness: past ~7, answer quality collapses and guessed answers become fake requirements. The cap triggers more scanning, never more asking.
- The urge to keep "just the raw findings somewhere" is the old unknowns file coming back — the tiers are the only durable output.
- Bootstrap builds Tier 1 and 2 only. A spec per map row is N files of speculative content; specs appear when work touches a unit.
