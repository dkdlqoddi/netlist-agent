"""SystemVerilog 계층형 더미 넷리스트 생성기 모듈.

반도체 회로의 계층 구조와 구성요소를 포함하는 더미 넷리스트를 생성합니다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def generate_dummy_netlist() -> str:
    """계층 구조를 갖춘 더미 SystemVerilog 넷리스트 텍스트를 반환합니다."""
    return r"""// =============================================================================
// 회로 설계: SystemVerilog 계층형 더미 넷리스트
// 최상위 모듈(chip_top) 및 하위 모듈(full_adder, dff_reg)로 구성됩니다.
// =============================================================================

/*
 * 하위 모듈 1: 1비트 전가산기 (full_adder)
 * 기본 논리 게이트들을 사용하여 덧셈을 수행합니다.
 */
module full_adder (
    input a,
    input b,
    input cin,
    output sum,
    output cout
);
    wire w_xor1;
    wire w_and1;
    wire w_and2;

    XOR2 u_xor1 (.A(a), .B(b), .Z(w_xor1));
    XOR2 u_xor2 (.A(w_xor1), .B(cin), .Z(sum));
    AND2 u_and1 (.A(a), .B(b), .Z(w_and1));
    AND2 u_and2 (.A(w_xor1), .B(cin), .Z(w_and2));
    OR2  u_or1  (.A(w_and1), .B(w_and2), .Z(cout));
endmodule

/*
 * 하위 모듈 2: D 플립플롭 레지스터 (dff_reg)
 * 클록 에지에 맞추어 1비트 데이터를 저장합니다.
 */
module dff_reg (
    input clk,
    input rst_n,
    input d,
    output q
);
    DFF u_dff (.CLK(clk), .RST_N(rst_n), .D(d), .Q(q));
endmodule

/*
 * 최상위 모듈: 4비트 누산기 코어 (chip_top)
 * 계층 구조, 버스 신호, 별칭 선언 및 이스케이프 식별자를 포함합니다.
 */
module chip_top (
    input clk,
    input rst_n,
    input [3:0] data_in,
    output [3:0] data_out
);
    wire [3:0] int_sum;
    logic [3:0] int_reg;
    wire int_net_a;
    wire int_net_b;
    wire cin;
    wire c0;
    wire c1;
    wire c2;
    wire c3;

    // 신호선 별칭 구문 (동일 전기적 신호 연결)
    alias int_net_a = int_net_b;

    // 4비트 전가산기 인스턴스 (하위 모듈 계층 연결)
    full_adder u_fa0 (.a(data_in[0]), .b(int_reg[0]), .cin(cin),  .sum(int_sum[0]), .cout(c0));
    full_adder u_fa1 (.a(data_in[1]), .b(int_reg[1]), .cin(c0),   .sum(int_sum[1]), .cout(c1));
    full_adder u_fa2 (.a(data_in[2]), .b(int_reg[2]), .cin(c1),   .sum(int_sum[2]), .cout(c2));
    full_adder u_fa3 (.a(data_in[3]), .b(int_reg[3]), .cin(c2),   .sum(int_sum[3]), .cout(c3));

    // 4비트 레지스터 인스턴스 (이스케이프 식별자 \bus[0]_reg  포함)
    dff_reg \bus[0]_reg  (.clk(clk), .rst_n(rst_n), .d(int_sum[0]), .q(data_out[0]));
    dff_reg u_dff1 (.clk(clk), .rst_n(rst_n), .d(int_sum[1]), .q(data_out[1]));
    dff_reg u_dff2 (.clk(clk), .rst_n(rst_n), .d(int_sum[2]), .q(data_out[2]));
    dff_reg u_dff3 (.clk(clk), .rst_n(rst_n), .d(int_sum[3]), .q(data_out[3]));

    // 이름 기반 핀 연결 및 빈 핀 연결 검증용 인스턴스
    spare_gate u_spare (.A(int_net_a), .B(int_net_b), .Z());
endmodule
"""


def write_dummy_netlist_file(filepath: str) -> str:
    """더미 넷리스트 텍스트를 파일로 저장하고 경로를 반환합니다."""
    target_path = Path(filepath)
    if target_path.parent:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_dummy_netlist()
    target_path.write_text(content, encoding="utf-8")
    return str(target_path)


def main(argv: list[str] | None = None) -> int:
    """명령줄 인자를 처리하여 더미 넷리스트를 출력하거나 파일로 저장합니다."""
    parser = argparse.ArgumentParser(
        description="계층형 SystemVerilog 더미 넷리스트를 생성합니다."
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        help="넷리스트를 저장할 파일 경로입니다."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일을 생성하지 않고 생성 로직만 검증합니다."
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        _ = generate_dummy_netlist()
        return 0

    if args.output:
        write_dummy_netlist_file(args.output)
    else:
        sys.stdout.write(generate_dummy_netlist())

    return 0


if __name__ == "__main__":
    sys.exit(main())
