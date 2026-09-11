# T01 [제목]

- 역할: (2–5 단어. 예: 구현, 테스트 작성, 문서 갱신, 마이그레이션, 정리)
- 웨이브: 1
- 선행: 없음
- 대상 spec: docs/<영역>/specs/<단위>.md
- 협업 스쿼드: swarm-worker (구현) ↔ swarm-verifier (검증) ↔ swarm-reviewer (리뷰)
- 소유 파일: `path/to/existing.py`, `path/to/new_file.py` (신규), `path/to/dir/`
- 참고 파일: `path/to/pattern.py:12-40` (따라 할 기존 코드), `docs/<영역>/rules.md`

<!-- One brief = one collaborative squad (builder, verifier, reviewer) operating on this task. Every path literal; every interface spelled out verbatim in 해야 할 일. 소유 파일 = the only paths this squad may modify. 참고 파일 are read-only. Collaboration between worker, verifier, and reviewer runs via send_message within a turn budget of 3 rounds. -->

## 목표

(2–4문장. 무엇을, 왜. 스펙의 어느 요구사항을 만족시키는지)

## 해야 할 일

1. (순서대로. 따라 할 기존 코드가 있으면 `path:line`으로 지목)
2.

## 협업 프로토콜

1. 구현(`swarm-worker`) 완료 후 `swarm-verifier`에게 `[PHASE: VERIFY_REQUEST]` 메시지를 보냅니다.
2. `swarm-verifier`가 검증을 수행하고 실패 시 피드백을 전달하면, `swarm-worker`가 수정 후 재검증을 요청합니다.
3. 검증 통과 시 `swarm-reviewer`에게 `[PHASE: REVIEW_REQUEST]`를 전송하고, 리뷰 피드백 반영 후 승인(LGTM)을 획득합니다 (최대 3회 티키타카 내 수렴).

## 완료 조건

- [ ] (확인 가능한 문장으로. "동작한다"가 아니라 "X를 호출하면 Y를 돌려준다")
- [ ]

## 검증

`(이 작업만 검사하는 명령 — 테스트 파일 하나, 린트, 스크립트)` 또는 `없음` (없으면 전체 검증이 이 작업의 파일을 덮는다고 목표에 밝힌다)

