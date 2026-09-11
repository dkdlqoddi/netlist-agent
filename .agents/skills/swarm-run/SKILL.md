---
name: swarm-run
description: Use when the user asks to run, continue, or resume the swarm (/swarm-run, "스웜 실행", "계획대로 병렬 실행") and docs/swarm/plan.md exists. Executes the plan written by the swarm-plan skill — one swarm-worker subagent per task, a whole 웨이브 at a time, concurrently — verifies each 웨이브 with the plan's 전체 검증 through a swarm-checker subagent, commits it, and records everything in docs/swarm/status.md and docs/swarm/results/<id>.md. Never plans and never edits tier documents.
---

# Swarm Run

You are the dispatcher, not the engineer. The plan was written with the full context; your job is to execute it literally, in parallel, and to record what happened. When something in the plan cannot be executed, record it and move on — never repair the plan.

## Before starting

1. Confirm `docs/swarm/plan.md` exists; otherwise stop and tell the user (Korean) to run `swarm-plan` first.
2. Run `python3 .agents/skills/swarm-plan/scripts/swarm_check.py docs/swarm/plan.md`. Any violation → stop and show it; fix the plan before running.
3. Run `git status --porcelain`. Changes outside `docs/swarm/` → stop and ask the user to commit or stash them; a 웨이브 commit must contain only swarm work.
4. Read `docs/swarm/plan.md`: the 작업 table (id, 웨이브, 선행), 동시 실행 상한, 전체 검증. Do not open the briefs — each worker reads its own.
5. If `docs/swarm/status.md` exists, this is a resume: keep 완료 rows, treat 실행 중 as 대기, continue from the first 웨이브 that has a task not 완료. Otherwise create it from `templates/status.md` in this skill's folder (one row per task, 상태 대기, 시도 0, 커밋 -) and run `mkdir -p docs/swarm/results`.

## Each 웨이브, in order

1. **Pick.** Tasks of this 웨이브 whose 선행 are all 완료 → dispatch. A task with a 선행 that is 실패 or 보류 → 상태 보류, 비고 `선행 <id> 실패`, skip.
2. **Dispatch Collaborative Squads.** Set a watchdog timer via `schedule(DurationSeconds=900, Prompt="웨이브 실행 시간 초과 감시: 타임아웃 도래 여부 점검", TimerCondition="any")`. ONE `invoke_subagent` call per batch launching the collaborative squad for each task:
   For each task, spawn:
   - `TypeName: swarm-worker`, Role: `<id> Builder`, Model: `flash`, Workspace: `inherit`
     Prompt: `Task brief: docs/swarm/tasks/<id>.md. Touch only 소유 파일. Collaborate with your assigned verifier and reviewer via send_message to run checks and review diffs. Write docs/swarm/results/<id>.md following .agents/skills/swarm-run/templates/result.md within at most 3 collaboration rounds, and reply with the 상태 line only.`
   - `TypeName: swarm-verifier`, Role: `<id> Verifier`, Model: `flash`, Workspace: `inherit`
     Prompt: `Verify task docs/swarm/tasks/<id>.md. Wait for [PHASE: VERIFY_REQUEST] from the worker, run the brief's 검증 command, and send back [PHASE: VERIFY_RESULT] PASS or FAIL with concise error summaries via send_message.`
   - `TypeName: swarm-reviewer`, Role: `<id> Reviewer`, Model: `pro`, Workspace: `inherit`
     Prompt: `Review task docs/swarm/tasks/<id>.md. Wait for [PHASE: REVIEW_REQUEST] from the worker, inspect git diff against rules.md and spec criteria, and send back [PHASE: REVIEW_FEEDBACK] or APPROVAL (LGTM) via send_message.`
   Provide each agent with their squad peers' conversation IDs.
   Set the dispatched rows to 실행 중 and 시도 1. If any agent is not found, define it once with `define_subagent` (using `.agents/agents/swarm-*.md`) and dispatch again; likewise for `swarm-checker` with `.agents/agents/swarm-checker.md`.
3. **Collect & Deadlock Guard.** Wait for every result message. If a watchdog timer notification arrives or an agent is unresponsive:
   - Run `manage_subagents(Action="list")` to inspect live state.
   - For hung or unresponsive squad subagents, cancel them with `manage_subagents(Action="kill", ConversationIds=[...])`.
   - In `docs/swarm/status.md`, mark hung tasks as `실패`, 비고 `타임아웃(데드락 가드 발동)`.
   For each completed task, read only the `- 상태:` line of `docs/swarm/results/<id>.md` into status.md (완료 / 부분 완료 / 실패). No result file → 실패, 비고 `결과 없음`.
4. **Verify the 웨이브.** ONE `invoke_subagent` entry: `TypeName: swarm-checker`, Role `웨이브 <n> 검증`, Model `flash`, Workspace `inherit`, Prompt: `Run exactly this command once and report failures only: <전체 검증>`. Write the outcome into the 웨이브 검증 table. 통과 → step 6.
5. **Retry once (Targeted Hotfix / Micro Self-Healing).** If the failure output isolates cleanly to files owned by a single task (or a specific subset of tasks), re-dispatch (as in step 2, 시도 2) ONLY that specific task squad with the targeted error message. Otherwise, re-dispatch every task of this 웨이브 whose 상태 is 완료 or 부분 완료, appending to the prompt: `The 웨이브 verification failed after your work. Failures: <checker output>. Fix only what lies inside your 소유 파일; if nothing there is yours, change nothing and reply 상태: 완료.` Collect, then verify again. Still failing → set 진행 끝남 and 전체 검증 최종 결과 실패, leave later 웨이브 rows 대기, and go to Finish — `swarm-plan` re-plans, and `/swarm-run` resumes from status.md.
6. **Commit.** `git add -A && git commit -q -m "swarm: 웨이브 <n> — <ids>"`; write the short hash into the 커밋 cell of the 웨이브's rows (`-` when there was nothing to commit).
7. Save status.md before starting the next 웨이브.

## Finish

- Set 진행 끝남 and 전체 검증 최종 결과 from the last checker run; `git add docs/swarm && git diff --cached --quiet || git commit -q -m "swarm: 상태 기록"` (a resume that changed nothing has nothing to commit).
- Reply in Korean: counts of 완료 / 부분 완료 / 실패 / 보류, the failing task ids with the checker's key message, and the next step: `다음 단계로 swarm-review를 실행하세요`.

## Rules

- Never edit `docs/swarm/plan.md`, `docs/swarm/tasks/`, or anything under `docs/<area>/`. Never create a task. Never do a task yourself — a task without a worker result is 실패, not your job.
- Never ask the user mid-run; the only stops are the three precondition failures and a 웨이브 that fails its retry.
- Keep your context small: the plan table, status.md, the 상태 lines, and checker summaries — never source files, never full logs.

## Gotchas

<!-- Append recurring failure points here as they surface; do not delete entries — correct a stale entry's referent instead. -->
- Dispatching one task per call serialises the swarm — every 웨이브 is ONE `invoke_subagent` call with many entries.
- A worker's reply is not the record; `docs/swarm/results/<id>.md` is. Missing file = 실패, whatever the reply said.
- Running the 전체 검증 yourself floods your context with logs — the checker returns failures only.
- Workspace `branch` gives each worker a private copy nobody merges — always `inherit`; disjoint 소유 파일 is what keeps the shared tree safe.
- `git add -A` commits whatever `.gitignore` lets through — in the first smoke test a `__pycache__` landed in a 웨이브 commit because the scratch project had none. The auditor flags such files as 주인 없음; the fix is the consumer's `.gitignore`, not a narrower add.
