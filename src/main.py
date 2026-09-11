"""반도체 넷리스트 파싱 및 SQLite 데이터베이스 적재 통합 파이프라인 진입점 모듈."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

try:
    from database import NetlistDB
    from dummy_generator import generate_dummy_netlist, write_dummy_netlist_file
    from models import Netlist, NetlistError
    from parser import NetlistParser
except ImportError:
    from src.database import NetlistDB
    from src.dummy_generator import generate_dummy_netlist, write_dummy_netlist_file
    from src.models import Netlist, NetlistError
    from src.parser import NetlistParser


def print_circuit_summary(db: NetlistDB) -> None:
    """데이터베이스에 적재된 회로 통계 및 요약을 콘솔에 출력합니다."""
    modules = db.get_modules()
    print("=== 회로 넷리스트 요약 리포트 ===")
    print(f"총 모듈 수: {len(modules)}")

    for mod in modules:
        mod_name = mod["name"]
        nets = db.get_nets(mod_name)
        instances = db.get_instances(mod_name)
        connections = db.get_connections(mod_name)
        aliases = db.get_aliases(mod_name)

        print(f"\n[모듈: {mod_name}]")
        print(f"  - 인스턴스 개수: {len(instances)}")
        print(f"  - 넷 개수: {len(nets)}")
        print(f"  - 핀 연결 개수: {len(connections)}")
        if aliases:
            alias_strs = [f"{net_a} = {net_b}" for net_a, net_b in aliases]
            print(f"  - 별칭 목록: {', '.join(alias_strs)}")
        else:
            print("  - 별칭 목록: 없음")


def build_parser() -> argparse.ArgumentParser:
    """CLI 명령줄 인자 파서를 구성합니다."""
    parser = argparse.ArgumentParser(
        description="반도체 SystemVerilog 넷리스트 파싱 및 SQLite 적재 통합 CLI 도구입니다."
    )
    parser.add_argument(
        "--generate-dummy",
        nargs="?",
        const="dummy_netlist.v",
        default=None,
        metavar="PATH",
        help="지정된 경로에 더미 넷리스트 파일을 생성합니다 (기본값: dummy_netlist.v).",
    )
    parser.add_argument(
        "--netlist",
        default=None,
        metavar="PATH",
        help="파싱할 넷리스트 파일 경로를 지정합니다. 미지정 시 인메모리 더미를 사용합니다.",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        metavar="PATH",
        help="SQLite 데이터베이스 파일 경로를 지정합니다 (기본값: :memory:).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="데이터베이스 적재 후 모듈별 통계 요약 리포트를 출력합니다.",
    )
    return parser


def run_pipeline(args: argparse.Namespace) -> int:
    """넷리스트 파이프라인을 순차적으로 실행합니다."""
    # 1. 더미 파일 생성 옵션 처리
    if args.generate_dummy is not None:
        created_path = write_dummy_netlist_file(args.generate_dummy)
        print(f"더미 넷리스트 파일 생성 완료: {created_path}")

    # 2. 넷리스트 파싱 수행
    parser = NetlistParser()
    if args.netlist is not None:
        netlist: Netlist = parser.parse_file(args.netlist)
    else:
        dummy_content = generate_dummy_netlist()
        netlist = parser.parse_string(dummy_content)

    # 3. 데이터베이스 초기화 및 저장
    with NetlistDB(args.db) as db:
        db.init_schema()
        db.save_netlist(netlist)

        # 4. 요약 리포트 출력
        if args.summary:
            print_circuit_summary(db)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """명령줄 인자를 받아 파이프라인을 실행하고 종료 코드를 반환합니다."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return run_pipeline(args)
    except NetlistError as err:
        sys.stderr.write(f"넷리스트 파싱 오류: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"실행 오류: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
