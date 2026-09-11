"""SQLite 기반 넷리스트 데이터베이스 저장소 모듈.

파싱된 넷리스트 도메인 모델을 SQLite 관계형 데이터베이스에 저장하고 조회합니다.
"""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from models import Netlist
except ImportError:
    from src.models import Netlist


class NetlistDB:
    """넷리스트 데이터베이스 관리 클래스."""

    def __init__(self, db_path: str = ":memory:") -> None:
        """데이터베이스 연결을 초기화하고 외래키 제약조건을 활성화합니다."""
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def init_schema(self) -> None:
        """6개 정규화 테이블 DDL을 생성합니다."""
        ddl_script = """
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            direction TEXT NOT NULL,
            width INTEGER DEFAULT 1,
            msb INTEGER DEFAULT 0,
            lsb INTEGER DEFAULT 0,
            FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
            UNIQUE(module_id, name)
        );

        CREATE TABLE IF NOT EXISTS nets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            width INTEGER DEFAULT 1,
            msb INTEGER DEFAULT 0,
            lsb INTEGER DEFAULT 0,
            is_implicit INTEGER DEFAULT 0,
            FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
            UNIQUE(module_id, name)
        );

        CREATE TABLE IF NOT EXISTS instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            cell_type TEXT NOT NULL,
            FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
            UNIQUE(module_id, name)
        );

        CREATE TABLE IF NOT EXISTS pins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id INTEGER NOT NULL,
            pin_name TEXT NOT NULL,
            net_name TEXT,
            FOREIGN KEY(instance_id) REFERENCES instances(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            net_a TEXT NOT NULL,
            net_b TEXT NOT NULL,
            FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE
        );
        """
        self.conn.executescript(ddl_script)
        self.conn.commit()

    def save_netlist(self, netlist: Netlist) -> None:
        """Netlist 도메인 모델을 단일 트랜잭션으로 일괄 저장합니다."""
        try:
            cursor = self.conn.cursor()
            for module in netlist.modules:
                cursor.execute(
                    "INSERT INTO modules (name) VALUES (?)",
                    (module.name,),
                )
                module_id = cursor.lastrowid

                if module.ports:
                    port_rows = [
                        (
                            module_id,
                            port.name,
                            port.direction,
                            port.width,
                            port.msb,
                            port.lsb,
                        )
                        for port in module.ports
                    ]
                    cursor.executemany(
                        """
                        INSERT INTO ports (module_id, name, direction, width, msb, lsb)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        port_rows,
                    )

                if module.wires:
                    net_rows = [
                        (
                            module_id,
                            wire.name,
                            wire.data_type,
                            wire.width,
                            wire.msb,
                            wire.lsb,
                            1 if wire.is_implicit else 0,
                        )
                        for wire in module.wires
                    ]
                    cursor.executemany(
                        """
                        INSERT INTO nets (module_id, name, data_type, width, msb, lsb, is_implicit)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        net_rows,
                    )

                all_pin_rows = []
                for instance in module.instances:
                    cursor.execute(
                        """
                        INSERT INTO instances (module_id, name, cell_type)
                        VALUES (?, ?, ?)
                        """,
                        (module_id, instance.instance_name, instance.cell_type),
                    )
                    instance_id = cursor.lastrowid
                    for conn in instance.connections:
                        all_pin_rows.append(
                            (instance_id, conn.pin_name, conn.net_name)
                        )

                if all_pin_rows:
                    cursor.executemany(
                        """
                        INSERT INTO pins (instance_id, pin_name, net_name)
                        VALUES (?, ?, ?)
                        """,
                        all_pin_rows,
                    )

                if module.aliases:
                    alias_rows = [
                        (module_id, alias.net_a, alias.net_b)
                        for alias in module.aliases
                    ]
                    cursor.executemany(
                        """
                        INSERT INTO aliases (module_id, net_a, net_b)
                        VALUES (?, ?, ?)
                        """,
                        alias_rows,
                    )

            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_modules(self) -> list[dict[str, Any]]:
        """모듈 전체 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM modules ORDER BY id")
        return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    def get_module(self, name: str) -> dict[str, Any] | None:
        """단일 모듈 정보를 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM modules WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1]}

    def get_ports(self, module_name: str) -> list[dict[str, Any]]:
        """모듈의 입출력 포트 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT p.name, p.direction, p.width, p.msb, p.lsb
            FROM ports p
            JOIN modules m ON p.module_id = m.id
            WHERE m.name = ?
            ORDER BY p.id
            """,
            (module_name,),
        )
        return [
            {
                "name": row[0],
                "direction": row[1],
                "width": row[2],
                "msb": row[3],
                "lsb": row[4],
            }
            for row in cursor.fetchall()
        ]

    def get_nets(self, module_name: str) -> list[dict[str, Any]]:
        """모듈의 신호선 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT n.name, n.data_type, n.width, n.is_implicit
            FROM nets n
            JOIN modules m ON n.module_id = m.id
            WHERE m.name = ?
            ORDER BY n.id
            """,
            (module_name,),
        )
        return [
            {
                "name": row[0],
                "data_type": row[1],
                "width": row[2],
                "is_implicit": bool(row[3]),
            }
            for row in cursor.fetchall()
        ]

    def get_instances(self, module_name: str) -> list[dict[str, Any]]:
        """모듈의 소자 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT i.name, i.cell_type
            FROM instances i
            JOIN modules m ON i.module_id = m.id
            WHERE m.name = ?
            ORDER BY i.id
            """,
            (module_name,),
        )
        return [
            {"name": row[0], "cell_type": row[1]}
            for row in cursor.fetchall()
        ]

    def get_connections(self, module_name: str) -> list[dict[str, Any]]:
        """모듈 내 핀 연결 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT i.name, i.cell_type, p.pin_name, p.net_name
            FROM pins p
            JOIN instances i ON p.instance_id = i.id
            JOIN modules m ON i.module_id = m.id
            WHERE m.name = ?
            ORDER BY p.id
            """,
            (module_name,),
        )
        return [
            {
                "instance_name": row[0],
                "cell_type": row[1],
                "pin_name": row[2],
                "net_name": row[3] if row[3] is not None else "",
            }
            for row in cursor.fetchall()
        ]

    def get_aliases(self, module_name: str) -> list[tuple[str, str]]:
        """모듈의 별칭 목록을 반환합니다."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT a.net_a, a.net_b
            FROM aliases a
            JOIN modules m ON a.module_id = m.id
            WHERE m.name = ?
            ORDER BY a.id
            """,
            (module_name,),
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def close(self) -> None:
        """데이터베이스 연결을 닫습니다."""
        self.conn.close()

    def __enter__(self) -> NetlistDB:
        """컨텍스트 매니저 진입."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """컨텍스트 매니저 종료 시 DB를 닫습니다."""
        self.close()


__all__ = ["NetlistDB"]
