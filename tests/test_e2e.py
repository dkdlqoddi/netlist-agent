"""전체 파이프라인 E2E(End-to-End) 통합 회귀 테스트 모듈."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any
import pytest

try:
    from database import NetlistDB
    from dummy_generator import generate_dummy_netlist
    from main import build_parser, main, run_pipeline
    from models import Netlist
    from parser import NetlistParser
except ImportError:
    from src.database import NetlistDB
    from src.dummy_generator import generate_dummy_netlist
    from src.main import build_parser, main, run_pipeline
    from src.models import Netlist
    from src.parser import NetlistParser


def test_e2e_programmatic_pipeline() -> None:
    """더미 생성부터 파싱, DB 적재 및 조회까지의 전체 파이프라인 흐름을 검증합니다."""
    # 1. 계층형 더미 넷리스트 생성
    raw_netlist = generate_dummy_netlist()
    assert "module chip_top" in raw_netlist
    assert "module full_adder" in raw_netlist
    assert "module dff_reg" in raw_netlist

    # 2. 넷리스트 파싱
    parser = NetlistParser()
    netlist = parser.parse_string(raw_netlist)
    assert len(netlist.modules) == 3

    # 3. SQLite DB 적재 및 스키마 초기화
    with NetlistDB(":memory:") as db:
        db.init_schema()
        db.save_netlist(netlist)

        # 4. 데이터베이스 조회 및 정합성 검증
        modules = db.get_modules()
        module_names = [m["name"] for m in modules]
        assert module_names == ["full_adder", "dff_reg", "chip_top"]

        # full_adder 모듈 검증
        fa_instances = db.get_instances("full_adder")
        assert len(fa_instances) == 5
        fa_nets = db.get_nets("full_adder")
        assert len(fa_nets) == 3
        fa_connections = db.get_connections("full_adder")
        assert len(fa_connections) == 15

        # dff_reg 모듈 검증
        dff_instances = db.get_instances("dff_reg")
        assert len(dff_instances) == 1
        dff_connections = db.get_connections("dff_reg")
        assert len(dff_connections) == 4

        # chip_top 모듈 검증
        top_instances = db.get_instances("chip_top")
        assert len(top_instances) == 9
        top_inst_names = [inst["name"] for inst in top_instances]
        assert r"\bus[0]_reg" in top_inst_names
        assert "u_spare" in top_inst_names

        top_aliases = db.get_aliases("chip_top")
        assert len(top_aliases) == 1
        assert top_aliases[0] == ("int_net_a", "int_net_b")

        top_connections = db.get_connections("chip_top")
        assert len(top_connections) == 39
        spare_conns = [c for c in top_connections if c["instance_name"] == "u_spare"]
        assert len(spare_conns) == 3
        z_conn = [c for c in spare_conns if c["pin_name"] == "Z"][0]
        assert z_conn["net_name"] == ""


def test_main_cli_default_in_memory_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """기본 인메모리 실행 및 --summary 옵션의 출력을 검증합니다."""
    exit_code = main(["--db", ":memory:", "--summary"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "=== 회로 넷리스트 요약 리포트 ===" in captured.out
    assert "총 모듈 수: 3" in captured.out
    assert "[모듈: full_adder]" in captured.out
    assert "[모듈: dff_reg]" in captured.out
    assert "[모듈: chip_top]" in captured.out
    assert "인스턴스 개수: 9" in captured.out
    assert "int_net_a = int_net_b" in captured.out
    assert captured.err == ""


def test_main_cli_generate_dummy_and_file_flow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """더미 파일 생성 및 생성된 파일 파싱과 DB 저장 흐름을 검증합니다."""
    dummy_file = tmp_path / "test_netlist.v"
    db_file = tmp_path / "test_netlist.db"

    # 1. 파일 생성 및 인메모리 파싱 동시 수행
    ret1 = main(["--generate-dummy", str(dummy_file)])
    assert ret1 == 0
    assert dummy_file.exists()
    assert dummy_file.stat().st_size > 0

    captured1 = capsys.readouterr()
    assert f"더미 넷리스트 파일 생성 완료: {dummy_file}" in captured1.out

    # 2. 생성된 파일을 파일 기반 DB에 적재
    ret2 = main(["--netlist", str(dummy_file), "--db", str(db_file), "--summary"])
    assert ret2 == 0
    assert db_file.exists()

    captured2 = capsys.readouterr()
    assert "=== 회로 넷리스트 요약 리포트 ===" in captured2.out

    # 3. 생성된 DB 파일의 내용 직접 검증
    with NetlistDB(str(db_file)) as db:
        modules = db.get_modules()
        assert len(modules) == 3


def test_main_cli_generate_dummy_default_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--generate-dummy 옵션에 인자가 없을 때 기본 파일명(dummy_netlist.v) 생성을 검증합니다."""
    monkeypatch.chdir(tmp_path)
    exit_code = main(["--generate-dummy"])
    assert exit_code == 0

    default_file = tmp_path / "dummy_netlist.v"
    assert default_file.exists()
    assert "module chip_top" in default_file.read_text(encoding="utf-8")


def test_main_cli_custom_netlist_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """사용자 지정 넷리스트 파일 파싱 및 정상 적재를 검증합니다."""
    custom_netlist = tmp_path / "custom.v"
    custom_netlist.write_text(
        """
        module simple_buf (input in, output out);
            BUF u_buf (.A(in), .Y(out));
        endmodule
        """,
        encoding="utf-8",
    )

    exit_code = main(["--netlist", str(custom_netlist), "--summary"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "[모듈: simple_buf]" in captured.out
    assert "인스턴스 개수: 1" in captured.out


def test_main_cli_file_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    """존재하지 않는 넷리스트 파일 지정 시 비정상 종료 및 에러 출력을 검증합니다."""
    exit_code = main(["--netlist", "non_existent_netlist_path.v"])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "넷리스트 파싱 오류" in captured.err
    assert "파일을 찾을 수 없습니다" in captured.err


def test_main_cli_syntax_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """문법 오류가 포함된 넷리스트 파일 처리 시 비정상 종료 및 에러 출력을 검증합니다."""
    bad_netlist = tmp_path / "bad.v"
    bad_netlist.write_text(
        """
        module broken (input a);
            invalid_unsupported_statement_here;
        endmodule
        """,
        encoding="utf-8",
    )

    exit_code = main(["--netlist", str(bad_netlist)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "넷리스트 파싱 오류" in captured.err
    assert "지원하지 않는 구문입니다" in captured.err


def test_main_cli_subprocess_execution() -> None:
    """독립 파이썬 서브프로세스로 CLI 실행 시 정상 동작 및 반환 코드를 검증합니다."""
    cmd = [sys.executable, "src/main.py", "--db", ":memory:", "--summary"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert "=== 회로 넷리스트 요약 리포트 ===" in proc.stdout
    assert proc.stderr == ""


def test_main_cli_subprocess_failure() -> None:
    """독립 파이썬 서브프로세스로 CLI 실행 시 실패 케이스의 반환 코드와 에러를 검증합니다."""
    cmd = [sys.executable, "src/main.py", "--netlist", "missing_file.v"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert "넷리스트 파싱 오류" in proc.stderr
