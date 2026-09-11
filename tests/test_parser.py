"""SystemVerilog 게이트 수준 넷리스트 파서 단위 테스트 모듈."""

from __future__ import annotations

from pathlib import Path
import pytest

from dummy_generator import generate_dummy_netlist
from models import NetlistError
from parser import NetlistParser


def test_parse_dummy_netlist() -> None:
    """더미 넷리스트 전체를 파싱하여 계층 구조와 구성요소들을 검증합니다."""
    parser = NetlistParser()
    content = generate_dummy_netlist()
    netlist = parser.parse_string(content)

    assert len(netlist.modules) == 3
    mod_names = [m.name for m in netlist.modules]
    assert mod_names == ["full_adder", "dff_reg", "chip_top"]

    # 1. full_adder 검증
    fa = netlist.modules[0]
    assert len(fa.ports) == 5
    assert [p.name for p in fa.ports] == ["a", "b", "cin", "sum", "cout"]
    assert all(p.width == 1 for p in fa.ports)
    assert len(fa.wires) == 3
    assert [w.name for w in fa.wires] == ["w_xor1", "w_and1", "w_and2"]
    assert len(fa.instances) == 5

    # 2. dff_reg 검증
    dff = netlist.modules[1]
    assert len(dff.ports) == 4
    assert [p.name for p in dff.ports] == ["clk", "rst_n", "d", "q"]
    assert len(dff.instances) == 1
    assert dff.instances[0].cell_type == "DFF"

    # 3. chip_top 검증
    top = netlist.modules[2]
    assert len(top.ports) == 4
    assert top.ports[2].name == "data_in"
    assert top.ports[2].width == 4
    assert top.ports[2].msb == 3
    assert top.ports[2].lsb == 0
    assert top.ports[3].name == "data_out"
    assert top.ports[3].width == 4

    # wires 검증 (wire 및 logic 버스 신호)
    wire_map = {w.name: w for w in top.wires}
    assert "int_sum" in wire_map
    assert wire_map["int_sum"].data_type == "wire"
    assert wire_map["int_sum"].width == 4
    assert "int_reg" in wire_map
    assert wire_map["int_reg"].data_type == "logic"
    assert wire_map["int_reg"].width == 4

    # alias 검증
    assert len(top.aliases) == 1
    assert top.aliases[0].net_a == "int_net_a"
    assert top.aliases[0].net_b == "int_net_b"

    # 이스케이프 식별자 인스턴스 검증 (\bus[0]_reg )
    inst_names = [inst.instance_name for inst in top.instances]
    assert r"\bus[0]_reg" in inst_names

    # 빈 핀 연결 검증 (.Z())
    spare = next(inst for inst in top.instances if inst.instance_name == "u_spare")
    z_conn = next(conn for conn in spare.connections if conn.pin_name == "Z")
    assert z_conn.net_name == ""


def test_parse_file(tmp_path: Path) -> None:
    """파일로부터 넷리스트를 읽어 정상 파싱하는지 검증합니다."""
    netlist_file = tmp_path / "test_circuit.v"
    content = generate_dummy_netlist()
    netlist_file.write_text(content, encoding="utf-8")

    parser = NetlistParser()
    netlist = parser.parse_file(str(netlist_file))
    assert len(netlist.modules) == 3
    assert netlist.modules[0].name == "full_adder"

    # 존재하지 않는 파일에 대한 예외 검증
    with pytest.raises(NetlistError) as exc_info:
        parser.parse_file(tmp_path / "non_existent.v")
    assert "찾을 수 없습니다" in str(exc_info.value)


def test_ansi_and_non_ansi_ports() -> None:
    """ANSI 스타일과 Non-ANSI 스타일 포트 선언을 모두 올바르게 파싱하는지 검증합니다."""
    parser = NetlistParser()

    # ANSI 스타일
    ansi_code = """
    module ansi_block (
        input clk,
        input [7:0] din,
        output [7:0] dout
    );
        INV u_inv (.A(clk), .Y(dout[0]));
    endmodule
    """
    nl_ansi = parser.parse_string(ansi_code)
    mod_ansi = nl_ansi.modules[0]
    assert len(mod_ansi.ports) == 3
    assert mod_ansi.ports[0].name == "clk"
    assert mod_ansi.ports[0].direction == "input"
    assert mod_ansi.ports[0].width == 1
    assert mod_ansi.ports[1].name == "din"
    assert mod_ansi.ports[1].direction == "input"
    assert mod_ansi.ports[1].width == 8
    assert mod_ansi.ports[1].msb == 7
    assert mod_ansi.ports[1].lsb == 0
    assert mod_ansi.ports[2].name == "dout"
    assert mod_ansi.ports[2].direction == "output"
    assert mod_ansi.ports[2].width == 8

    # Non-ANSI 스타일
    non_ansi_code = """
    module non_ansi_block (clk, rst_n, din, dout);
        input clk;
        input rst_n;
        input [15:0] din;
        output [15:0] dout;
        BUF u_buf (.I(clk), .O(dout[0]));
    endmodule
    """
    nl_non_ansi = parser.parse_string(non_ansi_code)
    mod_non_ansi = nl_non_ansi.modules[0]
    assert len(mod_non_ansi.ports) == 4
    assert [p.name for p in mod_non_ansi.ports] == ["clk", "rst_n", "din", "dout"]
    assert mod_non_ansi.ports[0].direction == "input"
    assert mod_non_ansi.ports[1].direction == "input"
    assert mod_non_ansi.ports[2].direction == "input"
    assert mod_non_ansi.ports[2].width == 16
    assert mod_non_ansi.ports[2].msb == 15
    assert mod_non_ansi.ports[2].lsb == 0
    assert mod_non_ansi.ports[3].direction == "output"
    assert mod_non_ansi.ports[3].width == 16


def test_wire_and_logic_bus_signals() -> None:
    """wire 및 logic 신호선 선언의 데이터 타입과 버스 폭 파싱을 검증합니다."""
    parser = NetlistParser()
    code = """
    module bus_test (input clk, output q);
        wire single_wire;
        logic single_logic;
        wire [31:0] data_bus;
        logic [7:0] ctrl_bus;
        wire w_a, w_b;

        GATE u1 (.A(clk), .B(single_wire), .Z(q));
    endmodule
    """
    nl = parser.parse_string(code)
    wires = {w.name: w for w in nl.modules[0].wires}

    assert wires["single_wire"].data_type == "wire"
    assert wires["single_wire"].width == 1
    assert wires["single_logic"].data_type == "logic"
    assert wires["single_logic"].width == 1
    assert wires["data_bus"].data_type == "wire"
    assert wires["data_bus"].width == 32
    assert wires["data_bus"].msb == 31
    assert wires["data_bus"].lsb == 0
    assert wires["ctrl_bus"].data_type == "logic"
    assert wires["ctrl_bus"].width == 8
    assert wires["w_a"].data_type == "wire"
    assert wires["w_b"].data_type == "wire"


def test_empty_and_named_pin_connections() -> None:
    """이름 기반 핀 연결 및 빈 핀 연결(.Z())이 정상 파싱되는지 검증합니다."""
    parser = NetlistParser()
    code = """
    module pin_test (input a, input b, output z);
        GATE u_gate (
            .IN1(a),
            .IN2(b),
            .NC1(),
            .NC2( ),
            .OUT(z)
        );
    endmodule
    """
    nl = parser.parse_string(code)
    inst = nl.modules[0].instances[0]
    conn_map = {c.pin_name: c.net_name for c in inst.connections}

    assert conn_map["IN1"] == "a"
    assert conn_map["IN2"] == "b"
    assert conn_map["NC1"] == ""
    assert conn_map["NC2"] == ""
    assert conn_map["OUT"] == "z"


def test_implicit_wire_creation() -> None:
    """선언되지 않은 신호선이 핀에 연결될 때 1비트 암시적 와이어로 자동 등록되는지 검증합니다."""
    parser = NetlistParser()
    code = """
    module implicit_test (input clk, output out_sig);
        wire declared_wire;

        INV u1 (.A(clk), .Y(undeclared_net1));
        INV u2 (.A(undeclared_net1), .Y(undeclared_net2));
        INV u3 (.A(undeclared_net2), .Y(declared_wire));
        INV u4 (.A(declared_wire), .Y(out_sig));
    endmodule
    """
    nl = parser.parse_string(code)
    mod = nl.modules[0]
    wires = {w.name: w for w in mod.wires}

    # 선언된 신호선은 is_implicit=False
    assert "declared_wire" in wires
    assert wires["declared_wire"].is_implicit is False

    # 미선언 신호선은 is_implicit=True
    assert "undeclared_net1" in wires
    assert wires["undeclared_net1"].is_implicit is True
    assert wires["undeclared_net1"].width == 1
    assert "undeclared_net2" in wires
    assert wires["undeclared_net2"].is_implicit is True

    # 포트(clk, out_sig)는 와이어 목록에 중복 등록되지 않아야 함
    assert "clk" not in wires
    assert "out_sig" not in wires

    # 중복 참조된 undeclared_net1이 단 한 번만 등록되었는지 확인
    assert [w.name for w in mod.wires].count("undeclared_net1") == 1


def test_escaped_identifiers() -> None:
    """역슬래시로 시작하는 이스케이프 식별자가 모든 위치에서 올바르게 보존되는지 검증합니다."""
    parser = NetlistParser()
    code = r"""
    module \escape[0]_mod  (
        input \clk[0] ,
        output \q[0] 
    );
        wire \int[0]_wire ;
        alias \int[0]_wire  = \clk[0] ;

        DFF \reg[0]_inst  (
            .CLK(\clk[0] ),
            .D(\int[0]_wire ),
            .Q(\q[0] )
        );
    endmodule
    """
    nl = parser.parse_string(code)
    mod = nl.modules[0]

    assert mod.name == r"\escape[0]_mod"
    assert mod.ports[0].name == r"\clk[0]"
    assert mod.ports[1].name == r"\q[0]"
    assert mod.wires[0].name == r"\int[0]_wire"
    assert mod.aliases[0].net_a == r"\int[0]_wire"
    assert mod.aliases[0].net_b == r"\clk[0]"
    assert mod.instances[0].instance_name == r"\reg[0]_inst"
    assert mod.instances[0].connections[0].net_name == r"\clk[0]"


def test_comments_and_directives_removal() -> None:
    """한 줄 주석, 블록 주석, 컴파일러 지시문 및 속성이 제거되는지 검증합니다."""
    parser = NetlistParser()
    code = """
    // 최상위 라이선스 주석
    /* 블록 주석 시작
       여러 줄에 걸친 주석
       블록 주석 끝 */
    `timescale 1ns/1ps
    (* dont_touch = "true" *)
    module comment_test (
        input in_a, // 인라인 한 줄 주석
        /* 인라인 블록 */ output out_z
    );
        // 내부 주석
        wire w1; /* 신호선 주석 */
        BUF u_buf (.I(in_a), .O(w1));
        BUF u_out (.I(w1), .O(out_z));
    endmodule
    """
    nl = parser.parse_string(code)
    assert len(nl.modules) == 1
    assert nl.modules[0].name == "comment_test"
    assert len(nl.modules[0].ports) == 2
    assert len(nl.modules[0].wires) == 1
    assert len(nl.modules[0].instances) == 2


def test_alias_statement() -> None:
    """별칭(alias) 구문이 올바르게 Alias 객체로 파싱되는지 검증합니다."""
    parser = NetlistParser()
    code = """
    module alias_mod (input a, output b);
        wire net1;
        wire net2;
        wire net3;
        alias net1 = net2;
        alias net2 = net3;
    endmodule
    """
    nl = parser.parse_string(code)
    aliases = nl.modules[0].aliases
    assert len(aliases) == 2
    assert aliases[0].net_a == "net1"
    assert aliases[0].net_b == "net2"
    assert aliases[1].net_a == "net2"
    assert aliases[1].net_b == "net3"


def test_parser_error_handling() -> None:
    """문법 오류 및 비정상 형식에 대해 NetlistError가 발생하는지 검증합니다."""
    parser = NetlistParser()

    # 1. endmodule 누락
    with pytest.raises(NetlistError) as exc1:
        parser.parse_string("module unclosed (input a); wire w;")
    assert "일치하지 않습니다" in str(exc1.value)

    # 2. 지원하지 않는 위치 기반 단자 연결
    with pytest.raises(NetlistError) as exc2:
        parser.parse_string("""
        module bad_conn (input a, output b);
            INV u_inv (a, b);
        endmodule
        """)
    assert "지원하지 않는" in str(exc2.value)

    # 3. 잘못된 본문 구문
    with pytest.raises(NetlistError) as exc3:
        parser.parse_string("""
        module bad_stmt (input a);
            invalid syntax statement without meaning;
        endmodule
        """)
    assert "지원하지 않는" in str(exc3.value)
