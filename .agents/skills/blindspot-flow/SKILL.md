---
name: blindspot-flow
description: Use when the user invokes /blindspot-flow or asks to run a feature through the full lifecycle end-to-end — thin orchestrator that bootstraps the area's tiers when missing, then sequences requirements-interview, blindspot-pass, explainer, then work-report notes mode through implementation and report mode at the end.
---

# Blindspot Flow

Thin orchestrator. All real logic lives in the four lifecycle skills — this skill only sequences them.

## Workflow

Run the stages below in order, invoking each with the Skill tool by name. Before each stage, look at the touched unit's `docs/<area>/specs/<unit>.md` (found through the 단위 table of `docs/<area>/map.md`): if the section that stage fills already has content for this feature (요구사항 for stage 1; for stage 2, no 열린 질문 row still marked blindspot-pass에서 점검; 동작 방식 for stage 3), tell the user (Korean) and offer 실행 or 건너뛰기. Between stages, confirm with the user before proceeding — they may stop or skip any stage.

0. If the area has no `docs/<area>/map.md`, say so (Korean) and offer `blindspot-pass` to bootstrap Tier 1 and 2 first
1. `requirements-interview` → 요구사항 and 결정 기록 rows in the unit spec
2. `blindspot-pass` → findings filed into rules, map, and spec
3. `explainer` → 목적과 배경, 동작 방식, 의도적 범위 제외 in the spec; map updated
4. Implementation — offer (Korean) 이 세션에서 직접 구현 or 에이전트 협업 네트워크(스웜)로 병렬 구현. In-session: `work-report` notes mode opens `docs/notes/<slug>.md`; implementation proceeds. Collaborative Network: `swarm-plan` writes and reviews `docs/swarm/` (squad briefs for worker, verifier, reviewer, audited across 5 network dimensions via `swarm-plan-reviewer`); then run `/swarm-run` (squads collaborate via `send_message`); then `swarm-review` audits the result and either loops back to `swarm-plan` for a delta round or continues to stage 5
5. When implementation is done: `work-report` report mode → tiers promoted, `docs/quiz.html` written; after the user passes the quiz, work-report records the 변경 이력 row and strictly deletes all intermediate working documents (`docs/notes/<slug>.md`, `docs/swarm/`), guaranteeing only the 3-tier living documents (`rules.md`, `map.md`, `specs/*.md`) and `docs/quiz.html` remain in `docs/`.

Do not inline a stage's logic here; if a stage needs fixing, fix that skill.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- Skipping a stage is the user's call, not yours — always surface the option, never silently skip.
- "Already done" is a judgment on section content for this feature, not on the spec file existing — a 확정 spec from last quarter still needs this feature's interview.
