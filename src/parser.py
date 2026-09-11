"""SystemVerilog 게이트 수준 넷리스트 파서 모듈.

SystemVerilog 넷리스트 파일을 읽어 도메인 모델(Netlist)로 변환합니다.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Union

try:
    from models import (
        Alias,
        Instance,
        Module,
        Netlist,
        NetlistError,
        PinConnection,
        Port,
        Wire,
    )
except ImportError:
    from src.models import (
        Alias,
        Instance,
        Module,
        Netlist,
        NetlistError,
        PinConnection,
        Port,
        Wire,
    )


def _remove_comments_and_directives(text: str) -> str:
    """주석 및 컴파일러 지시문을 제거합니다."""
    # 블록 주석 제거
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    # 한 줄 주석 제거
    text = re.sub(r"//.*", "", text)
    # 컴파일러 지시문(`timescale 등) 제거
    text = re.sub(r"^\s*`.*$", "", text, flags=re.MULTILINE)
    # 속성 문법((* ... *)) 제거
    text = re.sub(r"\(\*[\s\S]*?\*\)", "", text)
    return text


def _normalize_identifier(token: str) -> str:
    """식별자를 정규화합니다. 이스케이프 식별자의 선두 역슬래시를 유지합니다."""
    token = token.strip()
    return token


def _get_base_net_name(net: str) -> str:
    """비트 인덱스가 포함된 신호선에서 기본 이름을 추출합니다."""
    net = net.strip()
    if not net:
        return ""
    if net.startswith("\\"):
        return net
    m = re.match(r"^([^\[\s]+)", net)
    if m:
        return m.group(1)
    return net


def _is_constant_literal(net: str) -> bool:
    """신호선 이름이 Verilog 상수 리터럴인지 판별합니다."""
    if re.match(r"^\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+$", net):
        return True
    if re.match(r"^'[01xXzZ]$", net):
        return True
    if re.match(r"^\d+$", net):
        return True
    return False


class NetlistParser:
    """SystemVerilog 게이트 수준 넷리스트 구문 분석기."""

    def parse_string(self, content: str) -> Netlist:
        """문자열 형태의 넷리스트 내용을 파싱하여 Netlist 객체를 반환합니다."""
        cleaned = _remove_comments_and_directives(content)

        module_starts = list(re.finditer(r"\bmodule\b", cleaned))
        module_ends = list(re.finditer(r"\bendmodule\b", cleaned))
        if len(module_starts) != len(module_ends):
            raise NetlistError("모듈 선언과 종료(endmodule) 개수가 일치하지 않습니다.")

        # 모듈 정규식: module <name> [(<header>)] ; <body> endmodule
        module_pattern = re.compile(
            r"\bmodule\s+([^\s(;]+)\s*(?:\(([\s\S]*?)\))?\s*;([\s\S]*?)\bendmodule\b(?:\s*;)?",
            re.MULTILINE,
        )

        modules: list[Module] = []
        for match in module_pattern.finditer(cleaned):
            mod_name = _normalize_identifier(match.group(1))
            header_str = match.group(2)
            body_str = match.group(3)

            parsed_module = self._parse_module(mod_name, header_str, body_str)
            modules.append(parsed_module)

        return Netlist(modules=modules)

    def parse_file(self, filepath: Union[str, Path]) -> Netlist:
        """파일 경로로부터 넷리스트를 읽어 파싱합니다."""
        path = Path(filepath)
        if not path.is_file():
            raise NetlistError(f"넷리스트 파일을 찾을 수 없습니다: {filepath}")
        content = path.read_text(encoding="utf-8")
        return self.parse_string(content)

    def _parse_module(
        self,
        module_name: str,
        header_str: str | None,
        body_str: str,
    ) -> Module:
        """단일 모듈의 포트, 신호선, 소자, 별칭을 파싱합니다."""
        ports_dict: dict[str, Port] = {}
        port_order: list[str] = []
        wires_list: list[Wire] = []
        known_wires: set[str] = set()
        instances_list: list[Instance] = []
        aliases_list: list[Alias] = []

        # 1. 헤더 분석 (ANSI vs Non-ANSI)
        if header_str and header_str.strip():
            self._parse_module_header(
                header_str, ports_dict, port_order
            )

        # 2. 모듈 본문 명령문 단위 분석 (세미콜론 분리)
        statements = body_str.split(";")
        for raw_stmt in statements:
            stmt = raw_stmt.strip()
            if not stmt:
                continue

            # (1) Non-ANSI 포트 선언문: input/output
            port_match = re.match(
                r"^(input|output|inout)\s+(?:wire\s+|logic\s+|reg\s+)?(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([\s\S]+)$",
                stmt,
            )
            if port_match:
                self._handle_port_statement(
                    port_match, ports_dict, port_order
                )
                continue

            # (2) 신호선 선언문: wire/logic
            wire_match = re.match(
                r"^(wire|logic)\s+(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([\s\S]+)$",
                stmt,
            )
            if wire_match:
                self._handle_wire_statement(
                    wire_match, wires_list, known_wires
                )
                continue

            # (3) 별칭 선언문: alias
            alias_match = re.match(r"^alias\s+([\s\S]+)$", stmt)
            if alias_match:
                self._handle_alias_statement(alias_match, aliases_list)
                continue

            # (4) 소자 인스턴스화 구문: <cell_type> <inst_name> (...)
            inst_match = re.match(
                r"^\s*(\S+)\s+(\S+)\s*\(([\s\S]*)\)\s*$", stmt
            )
            if inst_match:
                self._handle_instance_statement(
                    inst_match,
                    instances_list,
                    ports_dict,
                    known_wires,
                    wires_list,
                )
                continue

            # 지원되지 않는 알 수 없는 구문 에러 처리
            raise NetlistError(f"지원하지 않는 구문입니다: {stmt[:30]}")

        # 정렬된 포트 목록 구성
        ports = [ports_dict[p] for p in port_order]

        return Module(
            name=module_name,
            ports=ports,
            wires=wires_list,
            instances=instances_list,
            aliases=aliases_list,
        )

    def _parse_module_header(
        self,
        header_str: str,
        ports_dict: dict[str, Port],
        port_order: list[str],
    ) -> None:
        """모듈 선언부 헤더의 포트 목록을 파싱합니다."""
        is_ansi = bool(re.search(r"\b(input|output|inout)\b", header_str))

        if is_ansi:
            # ANSI 스타일: input [msb:lsb] name, output name
            curr_dir = "input"
            curr_width = 1
            curr_msb = 0
            curr_lsb = 0

            for raw_item in header_str.split(","):
                item = raw_item.strip()
                if not item:
                    continue

                m = re.match(
                    r"^(input|output|inout)\s+(?:wire\s+|logic\s+|reg\s+)?(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([\s\S]+)$",
                    item,
                )
                if m:
                    curr_dir = m.group(1)
                    if m.group(2) and m.group(3):
                        curr_msb = int(m.group(2))
                        curr_lsb = int(m.group(3))
                        curr_width = abs(curr_msb - curr_lsb) + 1
                    else:
                        curr_msb = 0
                        curr_lsb = 0
                        curr_width = 1
                    name_part = m.group(4)
                else:
                    name_part = item

                port_name = _normalize_identifier(name_part)
                if port_name not in ports_dict:
                    port_obj = Port(
                        name=port_name,
                        direction=curr_dir,
                        width=curr_width,
                        msb=curr_msb,
                        lsb=curr_lsb,
                    )
                    ports_dict[port_name] = port_obj
                    port_order.append(port_name)
        else:
            # Non-ANSI 스타일: 포트 식별자 목록만 추출
            for raw_item in header_str.split(","):
                port_name = _normalize_identifier(raw_item)
                if port_name and port_name not in ports_dict:
                    ports_dict[port_name] = Port(
                        name=port_name,
                        direction="",
                        width=1,
                        msb=0,
                        lsb=0,
                    )
                    port_order.append(port_name)

    def _handle_port_statement(
        self,
        match: re.Match[str],
        ports_dict: dict[str, Port],
        port_order: list[str],
    ) -> None:
        """Non-ANSI 포트 방향 및 폭 선언문을 처리합니다."""
        direction = match.group(1)
        if match.group(2) and match.group(3):
            msb = int(match.group(2))
            lsb = int(match.group(3))
            width = abs(msb - lsb) + 1
        else:
            msb = 0
            lsb = 0
            width = 1

        names_str = match.group(4)
        for raw_name in names_str.split(","):
            port_name = _normalize_identifier(raw_name)
            if not port_name:
                continue
            if port_name in ports_dict:
                p = ports_dict[port_name]
                p.direction = direction
                p.width = width
                p.msb = msb
                p.lsb = lsb
            else:
                ports_dict[port_name] = Port(
                    name=port_name,
                    direction=direction,
                    width=width,
                    msb=msb,
                    lsb=lsb,
                )
                port_order.append(port_name)

    def _handle_wire_statement(
        self,
        match: re.Match[str],
        wires_list: list[Wire],
        known_wires: set[str],
    ) -> None:
        """wire 또는 logic 신호선 선언문을 처리합니다."""
        data_type = match.group(1)
        if match.group(2) and match.group(3):
            msb = int(match.group(2))
            lsb = int(match.group(3))
            width = abs(msb - lsb) + 1
        else:
            msb = 0
            lsb = 0
            width = 1

        names_str = match.group(4)
        for raw_name in names_str.split(","):
            wire_name = _normalize_identifier(raw_name)
            if not wire_name:
                continue
            if wire_name not in known_wires:
                wire_obj = Wire(
                    name=wire_name,
                    data_type=data_type,
                    width=width,
                    msb=msb,
                    lsb=lsb,
                    is_implicit=False,
                )
                wires_list.append(wire_obj)
                known_wires.add(wire_name)

    def _handle_alias_statement(
        self,
        match: re.Match[str],
        aliases_list: list[Alias],
    ) -> None:
        """별칭(alias) 연결 선언문을 처리합니다."""
        parts = [_normalize_identifier(p) for p in match.group(1).split("=")]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            for i in range(len(parts) - 1):
                aliases_list.append(Alias(net_a=parts[i], net_b=parts[i + 1]))

    def _handle_instance_statement(
        self,
        match: re.Match[str],
        instances_list: list[Instance],
        ports_dict: dict[str, Port],
        known_wires: set[str],
        wires_list: list[Wire],
    ) -> None:
        """소자 인스턴스화 구문을 파싱하고 암시적 신호선을 등록합니다."""
        cell_type = _normalize_identifier(match.group(1))
        inst_name = _normalize_identifier(match.group(2))
        conn_str = match.group(3).strip()

        connections: list[PinConnection] = []
        if conn_str:
            pin_regex = re.compile(r"\.\s*([^\s(]+)\s*\(\s*([^)]*?)\s*\)")
            matches = list(pin_regex.finditer(conn_str))
            if not matches:
                raise NetlistError(
                    f"지원하지 않는 단자 연결 형식입니다: {cell_type} {inst_name}"
                )

            for m in matches:
                pin_name = _normalize_identifier(m.group(1))
                raw_net = m.group(2).strip()
                net_name = _normalize_identifier(raw_net) if raw_net else ""
                connections.append(
                    PinConnection(pin_name=pin_name, net_name=net_name)
                )

                # 암시적 와이어 자동 등록 로직
                if net_name and not _is_constant_literal(net_name):
                    base_net = _get_base_net_name(net_name)
                    if (
                        base_net
                        and base_net not in ports_dict
                        and base_net not in known_wires
                    ):
                        known_wires.add(base_net)
                        implicit_wire = Wire(
                            name=base_net,
                            data_type="wire",
                            width=1,
                            msb=0,
                            lsb=0,
                            is_implicit=True,
                        )
                        wires_list.append(implicit_wire)

        inst_obj = Instance(
            instance_name=inst_name,
            cell_type=cell_type,
            connections=connections,
        )
        instances_list.append(inst_obj)


__all__ = ["NetlistParser"]
