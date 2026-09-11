# [주제] 스웜 계획

- 작성일: YYYY-MM-DD
- 기준 커밋: (계획 시점의 git rev-parse --short HEAD)
- 대상 spec: docs/<영역>/specs/<단위>.md
- 작업 노트: docs/notes/<slug>.md
- 동시 실행 상한: 8
- 전체 검증: `(rules.md 표준 명령의 test 명령 — 웨이브마다 실행)`
- 실행 방법: Antigravity에서 `/swarm-run`. 진행 상황은 docs/swarm/status.md, 작업별 결과는 docs/swarm/results/<id>.md

<!-- Written by the swarm-plan skill (Antigravity main session, strong model) and executed by the swarm-run skill (Antigravity subagents, fast model). The executor schedules from the 작업 table only and never opens a brief itself — every cell must be literal. id = T01, T02, ... = the brief file tasks/<id>.md. 웨이브 = execution round; tasks in one 웨이브 run concurrently, so their 소유 파일 (in the briefs) must not overlap — scripts/swarm_check.py enforces this. 선행 = comma-separated ids from earlier 웨이브, or 없음. A re-plan appends a 회차 row and rewrites only the briefs it names. -->

## 목표

(2–4문장. 이 스웜이 끝났을 때 무엇이 되어 있어야 하는지, 무엇은 이 스웜의 일이 아닌지)

## 작업

| id | 제목 | 역할 | 웨이브 | 선행 |
|---|---|---|---|---|

## 회차

<!-- One row per handoff. 범위 = 전체 or the ids re-planned this round. -->

| 회차 | 날짜 | 범위 | 비고 |
|---|---|---|---|
