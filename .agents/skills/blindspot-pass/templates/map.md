# [영역] 시스템 맵 (Tier 2)

- 최종 갱신: YYYY-MM-DD
- 코드 루트: (이 영역의 코드 경로)
- 읽는 법: 이 영역을 건드리는 작업이 rules.md 다음에 읽는다. 상세는 '단위' 표의 상세 명세로 내려간다. 150줄을 넘기지 않는다.

<!-- Append new rows at the END of each table so parallel branches conflict on single lines only. 영역 개요 and 하는 일 cells: plain Korean. 위치 / 계약 위치 / 거치는 단위 순서 cells: technical. -->

## 영역 개요

(3–5문장. 이 영역이 무엇을 책임지고 무엇을 책임지지 않는지, 코드를 본 적 없는 독자 기준)

## 단위

<!-- 단위 = kebab-case id = the spec filename specs/<단위>.md. 위치 = path or glob. 상세 명세 = specs/<단위>.md, or 없음 until a task first touches the unit. Never create a spec for every row at bootstrap. -->

| 단위 | 하는 일 | 위치 | 상세 명세 |
|---|---|---|---|

## 주요 흐름

| 흐름 | 시작점 | 거치는 단위 순서 |
|---|---|---|

## 통합 지점

<!-- 상대 = the other area, an external service, a database, CI. 계약 위치 = the file that defines the contract (schema, types, OpenAPI). -->

| 상대 | 방식 | 계약 위치 | 관련 단위 |
|---|---|---|---|

## 알려진 위험

<!-- Only risks that name two or more units. A single-unit risk goes to that unit's spec. -->

| 위험 | 영향 단위 | 상태 |
|---|---|---|
