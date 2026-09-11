"""도메인 데이터 모델 단위 테스트 모듈."""

from dataclasses import asdict

import pytest

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


def test_import_models() -> None:
    """모든 도메인 모델 클래스가 정상적으로 임포트되는지 확인한다."""
    assert Port is not None
    assert Wire is not None
    assert PinConnection is not None
    assert Instance is not None
    assert Alias is not None
    assert Module is not None
    assert Netlist is not None
    assert NetlistError is not None


def test_port_defaults_and_custom() -> None:
    """Port 객체의 기본값 및 사용자 지정 값이 정상 할당되는지 확인한다."""
    p_default = Port(name="clk", direction="input")
    assert p_default.name == "clk"
    assert p_default.direction == "input"
    assert p_default.width == 1
    assert p_default.msb == 0
    assert p_default.lsb == 0

    p_bus = Port(name="data", direction="output", width=8, msb=7, lsb=0)
    assert p_bus.name == "data"
    assert p_bus.direction == "output"
    assert p_bus.width == 8
    assert p_bus.msb == 7
    assert p_bus.lsb == 0


def test_wire_defaults_and_implicit() -> None:
    """Wire 객체의 기본값 및 is_implicit 플래그가 정상 작동하는지 확인한다."""
    w_default = Wire(name="w_clk")
    assert w_default.name == "w_clk"
    assert w_default.data_type == "wire"
    assert w_default.width == 1
    assert w_default.msb == 0
    assert w_default.lsb == 0
    assert w_default.is_implicit is False

    w_implicit = Wire(name="w_unreg", is_implicit=True)
    assert w_implicit.is_implicit is True

    w_logic = Wire(name="bus_logic", data_type="logic", width=16, msb=15, lsb=0)
    assert w_logic.data_type == "logic"
    assert w_logic.width == 16
    assert w_logic.msb == 15
    assert w_logic.lsb == 0


def test_pin_connection() -> None:
    """PinConnection 객체의 연결 및 빈 핀 처리를 확인한다."""
    conn = PinConnection(pin_name="A", net_name="net1")
    assert conn.pin_name == "A"
    assert conn.net_name == "net1"

    # 빈 핀의 경우 net_name이 빈 문자열이어야 함
    empty_conn = PinConnection(pin_name="NC")
    assert empty_conn.pin_name == "NC"
    assert empty_conn.net_name == ""

    explicit_empty = PinConnection(pin_name="NC2", net_name="")
    assert explicit_empty.net_name == ""


def test_instance_creation() -> None:
    """Instance 객체의 필드와 기본 연결 목록을 확인한다."""
    inst = Instance(instance_name="u_buf", cell_type="BUF_X1")
    assert inst.instance_name == "u_buf"
    assert inst.cell_type == "BUF_X1"
    assert inst.connections == []

    conn1 = PinConnection(pin_name="I", net_name="sig_in")
    conn2 = PinConnection(pin_name="O", net_name="sig_out")
    inst_with_conns = Instance(
        instance_name="u_buf2",
        cell_type="BUF_X2",
        connections=[conn1, conn2],
    )
    assert len(inst_with_conns.connections) == 2
    assert inst_with_conns.connections[0].pin_name == "I"


def test_alias_creation() -> None:
    """Alias 객체가 두 신호선 이름을 정상적으로 보존하는지 확인한다."""
    alias = Alias(net_a="net_top", net_b="net_internal")
    assert alias.net_a == "net_top"
    assert alias.net_b == "net_internal"


def test_module_and_netlist_hierarchy() -> None:
    """Module 및 Netlist 객체의 계층 구성 및 목록 초기화를 확인한다."""
    sub_module = Module(
        name="sub_block",
        ports=[Port(name="in_sig", direction="input")],
        wires=[Wire(name="w_local")],
        instances=[
            Instance(
                instance_name="u_gate",
                cell_type="INV_X1",
                connections=[PinConnection("A", "in_sig"), PinConnection("Y", "w_local")],
            )
        ],
        aliases=[Alias(net_a="w_local", net_b="in_sig")],
    )

    top_module = Module(name="top_block")
    assert top_module.ports == []
    assert top_module.wires == []
    assert top_module.instances == []
    assert top_module.aliases == []

    netlist = Netlist(modules=[sub_module, top_module])
    assert len(netlist.modules) == 2
    assert netlist.modules[0].name == "sub_block"
    assert netlist.modules[1].name == "top_block"


def test_netlist_error() -> None:
    """NetlistError가 기본 Exception을 상속하며 정상 발생/포착되는지 확인한다."""
    with pytest.raises(NetlistError) as exc_info:
        raise NetlistError("파싱 중 문법 오류가 발생했습니다.")
    assert "파싱 중 문법 오류" in str(exc_info.value)
    assert issubclass(NetlistError, Exception)


def test_slots_attribute() -> None:
    """데이터 클래스들이 slots=True로 생성되어 정의되지 않은 속성 추가 시 에러가 나는지 확인한다."""
    port = Port(name="p", direction="input")
    assert hasattr(port, "__slots__")
    with pytest.raises(AttributeError):
        port.undefined_attr = "invalid"  # type: ignore[attr-defined]

    wire = Wire(name="w")
    assert hasattr(wire, "__slots__")
    with pytest.raises(AttributeError):
        wire.undefined_attr = "invalid"  # type: ignore[attr-defined]

    pin = PinConnection(pin_name="P")
    assert hasattr(pin, "__slots__")
    with pytest.raises(AttributeError):
        pin.undefined_attr = "invalid"  # type: ignore[attr-defined]

    inst = Instance(instance_name="i", cell_type="c")
    assert hasattr(inst, "__slots__")
    with pytest.raises(AttributeError):
        inst.undefined_attr = "invalid"  # type: ignore[attr-defined]

    alias = Alias(net_a="a", net_b="b")
    assert hasattr(alias, "__slots__")
    with pytest.raises(AttributeError):
        alias.undefined_attr = "invalid"  # type: ignore[attr-defined]

    mod = Module(name="m")
    assert hasattr(mod, "__slots__")
    with pytest.raises(AttributeError):
        mod.undefined_attr = "invalid"  # type: ignore[attr-defined]

    netlist = Netlist()
    assert hasattr(netlist, "__slots__")
    with pytest.raises(AttributeError):
        netlist.undefined_attr = "invalid"  # type: ignore[attr-defined]


def test_serialization_asdict() -> None:
    """도메인 모델 인스턴스가 asdict를 통해 딕셔너리로 정상 직렬화되는지 확인한다."""
    wire = Wire(name="clk", is_implicit=False)
    port = Port(name="clk", direction="input")
    pin = PinConnection(pin_name="CK", net_name="clk")
    inst = Instance(instance_name="dff1", cell_type="DFF", connections=[pin])
    alias = Alias(net_a="clk", net_b="sys_clk")
    mod = Module(
        name="test_mod",
        ports=[port],
        wires=[wire],
        instances=[inst],
        aliases=[alias],
    )
    netlist = Netlist(modules=[mod])

    serialized = asdict(netlist)
    assert isinstance(serialized, dict)
    assert serialized["modules"][0]["name"] == "test_mod"
    assert serialized["modules"][0]["ports"][0]["name"] == "clk"
    assert serialized["modules"][0]["wires"][0]["is_implicit"] is False
    assert serialized["modules"][0]["instances"][0]["connections"][0]["pin_name"] == "CK"
    assert serialized["modules"][0]["aliases"][0]["net_a"] == "clk"
