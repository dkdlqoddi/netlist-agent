# core 시스템 맵 (Tier 2)

- 최종 갱신: 2026-09-11
- 코드 루트: src
- 읽는 법: 이 영역을 건드리는 작업이 rules.md 다음에 읽는다. 상세는 '단위' 표의 상세 명세로 내려간다. 150줄을 넘기지 않는다.

## 영역 개요

반도체 넷리스트 텍스트 파일을 분석하여 소자 및 연결망 토폴로지를 추출합니다.
추출된 회로 구성요소들을 관계형 스키마 구조로 변환하여 데이터베이스에 저장합니다.
별도의 외부 데이터베이스 서버나 무거운 파서 의존성 없이 표준 환경에서 실행됩니다.
실제 반도체 설계 넷리스트 형식과 호환되는 더미 데이터 및 검증 코드를 함께 제공합니다.

## 단위

| 단위 | 하는 일 | 위치 | 상세 명세 |
|---|---|---|---|
| netlist-model | 넷리스트의 핵심 도메인 객체와 데이터 구조 정의 | src/models.py | 없음 |
| netlist-parser | 넷리스트 텍스트를 읽어 도메인 객체로 파싱 | src/parser.py | specs/netlist-parser.md |
| db-store | 도메인 객체를 SQLite 데이터베이스에 구조화하여 적재 및 조회 | src/database.py | 없음 |
| dummy-generator | 회로 구성요소가 포함된 더미 넷리스트 파일 생성 | src/dummy_generator.py | 없음 |
| main-runner | 더미 생성 및 파싱과 DB 적재를 시연하는 실행 진입점 | src/main.py | 없음 |

## 주요 흐름

| 흐름 | 시작점 | 거치는 단위 순서 |
|---|---|---|
| 더미 넷리스트 생성 | dummy-generator | dummy-generator |
| 넷리스트 파싱 및 DB 적재 | netlist-parser | netlist-parser -> netlist-model -> db-store |
| 회로 연결망 조회 | db-store | db-store -> netlist-model |
| 전체 파이프라인 시연 | main-runner | main-runner -> dummy-generator -> netlist-parser -> db-store |

## 통합 지점

| 상대 | 방식 | 계약 위치 | 관련 단위 |
|---|---|---|---|
| Netlist 입력 파일 | 텍스트 파일 읽기 (Verilog/SystemVerilog 문법) | src/parser.py | netlist-parser |
| SQLite 스토리지 | Python 내장 sqlite3 라이브러리 및 SQL 스키마 | src/database.py | db-store |

## 알려진 위험

| 위험 | 영향 단위 | 상태 |
|---|---|---|
| 대용량 넷리스트 파싱 시 메모리 증가 및 DB 트랜잭션 락 병목 위험 | netlist-parser, db-store | 관찰 중 |
| 넷리스트 내 alias 구문 및 순환 참조로 인한 연결망 그래프 무결성 훼손 위험 | netlist-model, db-store | 관찰 중 |
| 모듈 정의 핀과 인스턴스 접속 핀의 식별자 혼동으로 인한 외래키 충돌 위험 | netlist-model, db-store | 관찰 중 |
