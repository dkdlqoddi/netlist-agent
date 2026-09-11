---
name: swarm-review
description: Use when an Antigravity swarm run has finished (docs/swarm/status.md says 진행 끝남) or the user asks to review, accept, or merge swarm results — audits every task result against its brief and the real diff via swarm-auditor, folds the workers' decisions into docs/notes/<slug>.md, then routes the residue to swarm-plan for a delta round or hands over to work-report report mode.
---

# Swarm Review

The swarm hands back a working tree and a pile of claims. This skill turns the claims into verified facts and the workers' decisions into notes before the merge gate sees any of it.

## Workflow

1. **Check the run is over.** Read `docs/swarm/status.md`. If 진행 is not 끝남, tell the user (Korean) the swarm is still running or was interrupted, and stop — `/swarm-run` resumes from the status file. Read `docs/swarm/plan.md` for the 기준 커밋, the 대상 spec, and the 전체 검증 command.

2. **Audit.** Spawn IN PARALLEL (one message, two `invoke_subagent` entries): `swarm-auditor` (`TypeName: swarm-auditor`, Model: `pro`, Workspace: `inherit`) with the plan path, `docs/swarm/tasks/`, `docs/swarm/results/`, the status path, and the 기준 커밋; and `check-runner` (`TypeName: check-runner`, Model: `flash`, Workspace: `inherit`) with the 전체 검증 command. Do not read the result files yourself — the auditor distills them.

3. **Fold decisions into the notes.** Ensure `docs/notes/<slug>.md` exists (the 작업 노트 line of the plan names it; create it from the `work-report` skill's `templates/notes.md`, installed at `.agents/skills/work-report/templates/notes.md`, when missing). For every 결정 line the auditor returned, append one notes entry in the notes-mode format, with 결정 주체 the task id, 계획과의 이탈 from the result's 브리프와 다르게 한 것, and 사용자 확인 필요 예 when the worker chose between options the spec does not settle. 막힌 것 lines become entries too, marked 사용자 확인 필요 예. This happens before report mode so the decisions surface in the quiz.

4. **Triage and route.** From the audit table and the check-runner result, sort the residue and tell the user (Korean, `ask_question` or chat message when more than one route is viable):
   - Everything 완료 확인 and 전체 검증 통과 → hand over: `work-report` report mode with the plan document path `docs/swarm/plan.md` so change-analyzer measures deviation against it.
   - A few small defects (범위 이탈 on one file, one 미완 checkbox) → fix them here under `work-report` notes mode, re-run the 전체 검증, then hand over as above.
   - Tasks 실패, 보류, 결과 없음, or 통합 위험 spanning tasks → `swarm-plan` re-plan round: it rewrites only those briefs (folding the 막힌 것 text in) and appends a 회차 row; then run `/swarm-run` again, then this skill again.
   Never merge, never write the 변경 이력 row, never edit tier documents here — work-report owns the gate.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- A worker's 완료 is a claim written by a model that could not see the other tasks; the auditor's diff evidence is the fact. Route on the audit table, never on the status file alone.
- Folding decisions after the quiz is too late — the quiz is generated from the notes and specs, so an unfolded worker decision is a decision the reviewer never sees.
- Reading twenty result files in the main context is the old raw-output pile; the auditor exists so this skill sees one table.
