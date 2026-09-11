---
name: work-report
description: "Use in two modes — (a) notes mode the moment implementation starts and whenever a non-obvious decision or plan deviation happens mid-work: append it to docs/notes/<slug>.md immediately; (b) report mode when work completes or before merge: analyze the diff via change-analyzer, promote the notes into the touched specs and map, and generate docs/quiz.html, the self-contained pre-merge quiz the user must pass before merging."
---

# Work Report

The work is territory; the tiers are the map you hand back. Keep the map honest while memory is fresh — never reconstructed at the end.

## Notes mode

Trigger: implementation starts, OR you make a non-obvious decision, pick a conservative option on an unexpected edge case, or deviate from the plan.

1. Ensure `docs/notes/<slug>.md` exists — if not, create it from `templates/notes.md` in this skill's folder, naming the target spec(s). Do not open the spec.
2. Append one Korean entry per event AT DECISION TIME (not batched later): 결정 / 이유 / 검토한 대안 / 보수적 선택 여부 / 계획과의 이탈 여부 / 사용자 확인 필요 / 반영 대상 (the spec section, or `rules.md` 불변 규칙, the entry will be promoted into).
3. A decision that seems to need user input: if it is reversible, take the conservative option, log it, and mark it 사용자 확인 필요 for the next checkpoint (stage boundary or report mode) instead of asking mid-flow. Ask immediately only when the choice is irreversible or destructive (data loss, external side effects, published contracts).
4. Continue working — notes mode never blocks implementation.

## Report mode

Trigger: work complete, pre-merge, or the user asks for a report.

1. **Analyze.** Spawn IN PARALLEL (one message, two `invoke_subagent` entries): `change-analyzer` (`TypeName: change-analyzer`) with the base ref (default: merge-base with the default branch — main, else master), the touched spec paths, the area `map.md` path (when it exists), and a plan document path when one exists (`docs/swarm/plan.md` when the work ran as a swarm); and `check-runner` (`TypeName: check-runner`) with the commands from `rules.md` 표준 명령 (or the project's known checks).
2. **Ask first.** Present every 사용자 확인 필요 item queued in `docs/notes/<slug>.md` as batched Korean questions BEFORE touching any tier file — the answers change what gets promoted.
3. **Promote into the tiers.** Sources: the notes, the change-analyzer output, the check-runner 검증 결과. If the primary unit has no spec yet (a cycle that started in notes mode), create it from the `explainer` skill's `templates/spec.md` (`.agents/skills/explainer/templates/spec.md` in consumer projects) with every heading present and 상태 초안, and set (or add) its 단위 row's 상세 명세 in `map.md` to `specs/<unit>.md`. If the area has no `map.md` at all (bootstrap never ran), do not create one: skip every map edit in this step and say so in the chat summary (Korean) so the user can run `blindspot-pass` later. In the primary unit's spec (and any other spec a note's 반영 대상 names): each note becomes a 결정 기록 row (one line, date first, 결정 주체 사용자 or 자체); edge cases met during implementation go to 엣지케이스와 제약; things cut go to 의도적 범위 제외; 동작 방식 is corrected to what was actually built (adjust the affected sentences — do not rewrite explainer's prose wholesale). Apply every `문서 갱신 필요` item: 단위 rows and 위치 in `map.md`, changed 통합 지점, changed 불변 규칙 in `rules.md`. If the primary spec's 의도적 범위 제외 is still empty, fill it or state why the scope is total. When a 결정 기록 row you write answers an existing 열린 질문 row, delete that row in the same edit. Update 최종 갱신. Then, for every tier file you edited, spawn `doc-verifier` (`TypeName: doc-verifier`) naming the sections you touched, fix every issue, and run `python3 .agents/skills/work-report/scripts/docs_check.py <every edited tier file>` (`scripts/docs_check.py` in this skill's folder).
4. **Generate the quiz.** Copy `templates/quiz.html` from this skill's folder over `docs/quiz.html` (one file, overwritten every cycle); fill the title, the meta line (target spec path and base commit — outside the summary block), the 변경 요약 block, and the `QUESTIONS` array with 4–6 Korean multiple-choice questions targeting what a reviewer must understand: 위험 지점, 동작 변화, 계획 이탈, 범위 제외. Wrong options must be plausible. The quiz reader is a non-developer — write every sentence for someone who has never seen the code:
   - Ask what happens or what could go wrong, never how the code looks. No code syntax, identifiers, file paths, or shell fragments inside question or option sentences; no arrow shorthand (A→B); no unexplained jargon.
   - Unavoidable technical terms: plain Korean first, term in parentheses — e.g. "설정 파일이 깨져 있으면(잘못된 JSON)".
   - The quiz is a self-contained gate, not an exam: the 변경 요약 plus the question's own scenario sentence must contain every fact needed to answer. Never quiz recall of process history (which step, review, or commit did what); ask the reader to apply a summary fact — what changes for users, what could go wrong, what was deliberately not done.
   - A question is one scenario sentence plus one question sentence — one fact each, ≤25 어절 per sentence. Options are complete sentences, one idea each, ≤40 Korean characters, parallel in form — a conspicuously long option must not give away the answer. Vary the correct answer's position across questions.
   - Every question gets an `explain` field: 2–3 plain Korean sentences (same ≤25 어절 bar) on why the answer is right and why the most tempting wrong option is wrong. Technical terms and file paths belong here (in parentheses), not in questions.
   - The summary block follows the same sentence rules: user-visible changes only, no commit hashes, no arrows — and it must state every fact the questions rely on.
   - Before saving, self-check every question: could someone who read only the 변경 요약 answer it? Is every sentence one fact within 25 어절, every option within 40 characters? If not, rewrite.
   - Then run the countable check: `python3 .agents/skills/work-report/scripts/docs_check.py docs/quiz.html`. Fix every reported violation before the gate.
   Also print in chat (Korean) the 3–5 sentence 사람용 요약 and the 리뷰 포인트 (파일:라인 — technical, for code reviewers); put both in the PR body when the project uses pull requests.
5. **Gate.** Tell the user (Korean): 퀴즈를 브라우저로 열어 전부 맞히기 전에는 머지하지 말 것. Never declare the work merged/done until the user confirms passing. When they confirm:
   - Append one 변경 이력 row to the primary spec (one per area when two areas were touched) — 날짜 | 변경 요약 in one sentence | 기준 커밋 | 검증 (the check-runner 총평) | 퀴즈 통과 date.
   - Inspect `docs/notes/<slug>.md` and `docs/swarm/results/` for recurring runtime rules, conventions, or environment pitfalls; promote any generalizable invariant into `docs/<area>/rules.md` (Tier 1, respecting the ≤60 lines cap) under `## 관례` or `## 엣지케이스와 제약`.
   - Strictly delete ALL intermediate working documents: delete `docs/notes/<slug>.md` (and remove `docs/notes/` if empty) and delete `docs/swarm/` completely (`rm -rf docs/swarm`), ensuring ONLY the 3 tiers (`rules.md`, `map.md`, `specs/*.md`) and the latest `docs/quiz.html` remain in `docs/`.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- Notes written after the fact are fiction; append at decision time.
- Quiz questions about trivia (file names, line counts) are worthless — ask about behavior and risk.
- A quiz written in the author's head-language (code syntax, arrows, compressed jargon) locks out non-developers; every sentence must survive the "reader has never seen the code" test.
- A 변경 요약 written in engineer-speak (arrows, raw jargon) locks stakeholders out — but only the summary and the spec's non-developer sections: 리뷰 포인트, 근거 cells, and 엣지케이스 처리 are technical by design; simplifying them destroys their function.
- Clean vocabulary does not equal readable: a 40+ 어절 sentence with nested clauses locks out the same readers even with zero jargon — the one-fact / ≤25 어절 bar is part of the standard.
- A quiz that needs process-history recall is an exam, not a gate; if the 변경 요약 cannot support the answer, fix the summary or drop the question.
- Stopping mid-work to ask about a reversible choice trades flow for false safety — conservative default + note + checkpoint batch keeps the decision visible without blocking. Immediate questions are reserved for irreversible or destructive choices.
- Self-check alone has let over-length sentences slip through; sentence and option length are countable, so `scripts/docs_check.py` is the enforcement — eyeballing is not.
- Opening the spec "just to check" during implementation turns notes mode into a rewrite session — notes go to `docs/notes/<slug>.md` only; the spec changes at promotion time.
- Promoting before asking the 사용자 확인 필요 batch writes guesses into shared documents every later cycle trusts — ask first, promote second.
