"""더미 넷리스트 생성기 단위 테스트 모듈."""

from __future__ import annotations

from pathlib import Path

from dummy_generator import generate_dummy_netlist, main, write_dummy_netlist_file


def test_required_keywords_present() -> None:
    """명세에 정의된 필수 키워드가 넷리스트에 모두 포함되어 있는지 검증합니다."""
    netlist = generate_dummy_netlist()

    required_keywords = [
        "full_adder",
        "dff_reg",
        "chip_top",
        "wire",
        "logic",
        "alias",
        ".Z()",
        "\\bus[0]_reg ",
    ]

    for keyword in required_keywords:
        assert keyword in netlist, f"필수 키워드 누락: {keyword}"


def test_module_structure_and_ansi_ports() -> None:
    """하위 모듈과 최상위 모듈의 구조 및 ANSI 포트 선언을 검증합니다."""
    netlist = generate_dummy_netlist()

    # ANSI 스타일 모듈 선언 검증
    assert "module full_adder (" in netlist
    assert "module dff_reg (" in netlist
    assert "module chip_top (" in netlist
    assert netlist.count("endmodule") == 3

    # full_adder 포트 및 게이트 검증
    assert "input a" in netlist
    assert "input b" in netlist
    assert "input cin" in netlist
    assert "output sum" in netlist
    assert "output cout" in netlist
    assert "XOR2" in netlist
    assert "AND2" in netlist
    assert "OR2" in netlist

    # dff_reg 포트 및 게이트 검증
    assert "input clk" in netlist
    assert "input rst_n" in netlist
    assert "input d" in netlist
    assert "output q" in netlist
    assert "DFF" in netlist

    # chip_top 포트, 신호선 및 인스턴스 검증
    assert "input [3:0] data_in" in netlist
    assert "output [3:0] data_out" in netlist
    assert "wire [3:0] int_sum;" in netlist
    assert "logic [3:0] int_reg;" in netlist
    assert "alias int_net_a = int_net_b;" in netlist

    # full_adder 4개 인스턴스
    for i in range(4):
        assert f"u_fa{i}" in netlist

    # dff_reg 4개 인스턴스 (이스케이프 식별자 1개 + 일반 식별자 3개)
    assert r"\bus[0]_reg " in netlist
    for i in range(1, 4):
        assert f"u_dff{i}" in netlist

    # 주석 검증 (한 줄 주석 및 블록 주석)
    assert "//" in netlist
    assert "/*" in netlist
    assert "*/" in netlist


def test_write_dummy_netlist_file(tmp_path: Path) -> None:
    """파일 저장 함수가 지정된 경로에 올바르게 파일을 생성하는지 검증합니다."""
    target_file = tmp_path / "sub_dir" / "test_netlist.v"
    returned_path = write_dummy_netlist_file(str(target_file))

    assert returned_path == str(target_file)
    assert target_file.is_file()

    content = target_file.read_text(encoding="utf-8")
    assert content == generate_dummy_netlist()


def test_cli_main_stdout(capsys) -> None:
    """인자 없이 실행 시 표준 출력으로 넷리스트가 출력되는지 검증합니다."""
    ret = main([])
    captured = capsys.readouterr()

    assert ret == 0
    assert captured.out == generate_dummy_netlist()
    assert captured.err == ""


def test_cli_main_output_file(tmp_path: Path, capsys) -> None:
    """--output 인자 전달 시 파일이 생성되고 표준 출력은 비어있는지 검증합니다."""
    out_file = tmp_path / "cli_out.v"
    ret = main(["--output", str(out_file)])
    captured = capsys.readouterr()

    assert ret == 0
    assert captured.out == ""
    assert out_file.is_file()
    assert out_file.read_text(encoding="utf-8") == generate_dummy_netlist()


def test_cli_main_dry_run(tmp_path: Path, capsys) -> None:
    """--dry-run 옵션 시 파일이 생성되지 않고 정상 종료되는지 검증합니다."""
    out_file = tmp_path / "should_not_exist.v"
    ret = main(["--dry-run", "--output", str(out_file)])
    captured = capsys.readouterr()

    assert ret == 0
    assert not out_file.exists()
    assert captured.out == ""

    # output 없이 dry-run 단독 실행
    ret_no_out = main(["--dry-run"])
    captured_no_out = capsys.readouterr()
    assert ret_no_out == 0
    assert captured_no_out.out == ""
