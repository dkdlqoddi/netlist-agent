"""NetlistDB 데이터베이스 연동 및 무결성 단위 테스트 모듈."""

import sqlite3
from typing import Any
import pytest

from database import NetlistDB
from models import (
    Alias,
    Instance,
    Module,
    Netlist,
    PinConnection,
    Port,
    Wire,
)


@pytest.fixture
def db() -> Any:
    """인메모리 NetlistDB 인스턴스를 생성하고 스키마를 초기화하는 픽스처."""
    net_db = NetlistDB(":memory:")
    net_db.init_schema()
    yield net_db
    net_db.close()


def test_init_schema_creates_all_tables(db: NetlistDB) -> None:
    """스키마 초기화 시 6개 핵심 테이블이 정상 생성되는지 확인한다."""
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {"modules", "ports", "nets", "instances", "pins", "aliases"}
    assert expected_tables.issubset(tables)


def test_foreign_key_constraints(db: NetlistDB) -> None:
    """외래키 제약조건이 활성화되어 잘못된 참조 시 에러가 발생하는지 확인한다."""
    cursor = db.conn.cursor()
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO ports (module_id, name, direction) VALUES (?, ?, ?)",
            (999, "clk", "input"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO nets (module_id, name, data_type) VALUES (?, ?, ?)",
            (999, "w1", "wire"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO instances (module_id, name, cell_type) VALUES (?, ?, ?)",
            (999, "u1", "INV_X1"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO pins (instance_id, pin_name, net_name) VALUES (?, ?, ?)",
            (999, "A", "net1"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO aliases (module_id, net_a, net_b) VALUES (?, ?, ?)",
            (999, "net_a", "net_b"),
        )


def test_cascade_delete(db: NetlistDB) -> None:
    """모듈 삭제 시 연관된 포트, 신호선, 소자, 핀이 연쇄 삭제되는지 확인한다."""
    mod = Module(
        name="cascade_mod",
        ports=[Port(name="in1", direction="input")],
        wires=[Wire(name="w1")],
        instances=[
            Instance(
                instance_name="u1",
                cell_type="BUF",
                connections=[PinConnection(pin_name="I", net_name="in1")],
            )
        ],
        aliases=[Alias(net_a="w1", net_b="in1")],
    )
    netlist = Netlist(modules=[mod])
    db.save_netlist(netlist)

    # 모듈 삭제 수행
    db.conn.execute("DELETE FROM modules WHERE name = ?", ("cascade_mod",))
    db.conn.commit()

    assert db.get_ports("cascade_mod") == []
    assert db.get_nets("cascade_mod") == []
    assert db.get_instances("cascade_mod") == []
    assert db.get_connections("cascade_mod") == []
    assert db.get_aliases("cascade_mod") == []


def test_save_and_query_netlist(db: NetlistDB) -> None:
    """Netlist 객체 적재 후 각 조회 메서드가 올바른 형식으로 데이터를 반환하는지 확인한다."""
    sub_module = Module(
        name="adder_1bit",
        ports=[
            Port(name="a", direction="input", width=1),
            Port(name="b", direction="input", width=1),
            Port(name="sum", direction="output", width=1),
        ],
        wires=[
            Wire(name="w_xor", data_type="wire", width=1, is_implicit=False),
            Wire(name="w_auto", data_type="wire", width=1, is_implicit=True),
        ],
        instances=[
            Instance(
                instance_name="u_xor1",
                cell_type="XOR2",
                connections=[
                    PinConnection(pin_name="A", net_name="a"),
                    PinConnection(pin_name="B", net_name="b"),
                    PinConnection(pin_name="Z", net_name="w_xor"),
                ],
            ),
            Instance(
                instance_name="u_spare",
                cell_type="DUMMY",
                connections=[PinConnection(pin_name="NC", net_name="")],
            ),
        ],
        aliases=[Alias(net_a="w_xor", net_b="w_auto")],
    )

    top_module = Module(
        name="top_core",
        ports=[Port(name="clk", direction="input")],
    )

    netlist = Netlist(modules=[sub_module, top_module])
    db.save_netlist(netlist)

    # 1. get_modules 테스트
    modules = db.get_modules()
    assert len(modules) == 2
    assert modules[0]["name"] == "adder_1bit"
    assert modules[1]["name"] == "top_core"

    # 2. get_module 테스트
    mod_info = db.get_module("adder_1bit")
    assert mod_info is not None
    assert mod_info["name"] == "adder_1bit"
    assert db.get_module("non_existent") is None

    # 3. get_nets 테스트 (is_implicit bool 타입 확인)
    nets = db.get_nets("adder_1bit")
    assert len(nets) == 2
    assert nets[0] == {
        "name": "w_xor",
        "data_type": "wire",
        "width": 1,
        "is_implicit": False,
    }
    assert nets[1] == {
        "name": "w_auto",
        "data_type": "wire",
        "width": 1,
        "is_implicit": True,
    }
    assert isinstance(nets[0]["is_implicit"], bool)

    # 4. get_instances 테스트
    instances = db.get_instances("adder_1bit")
    assert len(instances) == 2
    assert instances[0] == {"name": "u_xor1", "cell_type": "XOR2"}
    assert instances[1] == {"name": "u_spare", "cell_type": "DUMMY"}

    # 5. get_connections 테스트 (빈 핀 포함)
    conns = db.get_connections("adder_1bit")
    assert len(conns) == 4
    assert conns[0] == {
        "instance_name": "u_xor1",
        "cell_type": "XOR2",
        "pin_name": "A",
        "net_name": "a",
    }
    assert conns[3] == {
        "instance_name": "u_spare",
        "cell_type": "DUMMY",
        "pin_name": "NC",
        "net_name": "",
    }

    # 6. get_aliases 테스트
    aliases = db.get_aliases("adder_1bit")
    assert len(aliases) == 1
    assert aliases[0] == ("w_xor", "w_auto")

    # 7. get_ports 테스트
    ports = db.get_ports("adder_1bit")
    assert len(ports) == 3
    assert ports[0]["name"] == "a"
    assert ports[0]["direction"] == "input"


def test_atomic_transaction_rollback(db: NetlistDB) -> None:
    """적재 도중 오류가 발생할 때 전체 트랜잭션이 롤백되는지 확인한다."""
    # 동일 모듈 내 중복 포트 이름으로 인한 UNIQUE 제약 위반 유도
    invalid_mod = Module(
        name="invalid_mod",
        ports=[
            Port(name="dup_port", direction="input"),
            Port(name="dup_port", direction="output"),
        ],
    )
    netlist = Netlist(modules=[invalid_mod])

    with pytest.raises(sqlite3.IntegrityError):
        db.save_netlist(netlist)

    # 롤백 검증: invalid_mod가 모듈 테이블에 전혀 남아있지 않아야 함
    assert db.get_modules() == []
    assert db.get_module("invalid_mod") is None


def test_context_manager() -> None:
    """컨텍스트 매니저를 통해 정상적으로 생성 및 종료되는지 확인한다."""
    with NetlistDB(":memory:") as db:
        db.init_schema()
        assert db.get_modules() == []
