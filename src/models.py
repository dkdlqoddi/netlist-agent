"""넷리스트 핵심 도메인 데이터 모델 정의 모듈."""

from __future__ import annotations

from dataclasses import dataclass, field


class NetlistError(Exception):
    """넷리스트 도메인 최상위 예외 클래스."""


@dataclass(slots=True)
class Port:
    """모듈의 입출력 포트 정의."""

    name: str
    direction: str  # 'input' | 'output'
    width: int = 1
    msb: int = 0
    lsb: int = 0


@dataclass(slots=True)
class Wire:
    """모듈 내부 신호선 정의."""

    name: str
    data_type: str = "wire"  # 'wire' | 'logic'
    width: int = 1
    msb: int = 0
    lsb: int = 0
    is_implicit: bool = False


@dataclass(slots=True)
class PinConnection:
    """소자 인스턴스의 핀과 신호선 간 연결 정보."""

    pin_name: str
    net_name: str = ""


@dataclass(slots=True)
class Instance:
    """부품 소자 인스턴스 정보."""

    instance_name: str
    cell_type: str
    connections: list[PinConnection] = field(default_factory=list)


@dataclass(slots=True)
class Alias:
    """전기적으로 동일한 두 신호선 간 별칭 선언."""

    net_a: str
    net_b: str


@dataclass(slots=True)
class Module:
    """회로 모듈 정의."""

    name: str
    ports: list[Port] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)
    aliases: list[Alias] = field(default_factory=list)


@dataclass(slots=True)
class Netlist:
    """전체 넷리스트 도메인 모델 최상위 루트."""

    modules: list[Module] = field(default_factory=list)


__all__ = [
    "NetlistError",
    "Port",
    "Wire",
    "PinConnection",
    "Instance",
    "Alias",
    "Module",
    "Netlist",
]
