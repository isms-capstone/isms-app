"""Opt-in upgrade QA, allowed only on the empty disposable SIM test database."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


@pytest.mark.skipif(
    os.getenv("SIM_MIGRATION_QA") != "1", reason="Requires empty disposable MariaDB"
)
def test_upgrade_preserves_populated_wrk_data_and_builds_sim_index():
    from app.core.config import settings
    from app.db.session import engine

    assert settings.MARIADB_SERVER == "127.0.0.1"
    assert settings.MARIADB_PORT == 5437 and settings.MARIADB_DB == "isms_registry_qa"
    assert inspect(engine).get_table_names() == [], (
        "Refuse to overwrite an existing database"
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "wrkcat01")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO roles(id,name) VALUES(70291,'Admin')"))
        connection.execute(
            text(
                "INSERT INTO users(id,username,email,hashed_password,role_id,is_active,created_at,updated_at) VALUES(70291,'sim-migration','migration@example.org','unused',70291,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO ticket(id,ticket_no,subject,status,created_by_id,reported_at,created_at,sla_breached,reopen_count,is_exam_window) VALUES(70291,'DVHT-MIGRATION-70291','ข้อมูลเดิมก่อนอัปเดตระบบ','CLOSED',70291,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,0,2,0)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO ticket_worklogs(id,ticket_id,author_id,message,is_internal,channel,created_at) VALUES(70291,70291,70291,'Migration internal note',1,NULL,CURRENT_TIMESTAMP)"
            )
        )
        before = dict(
            connection.execute(text("SELECT * FROM ticket_worklogs WHERE id=70291"))
            .mappings()
            .one()
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            dict(
                connection.execute(text("SELECT * FROM ticket_worklogs WHERE id=70291"))
                .mappings()
                .one()
            )
            == before
        )
        assert connection.scalar(text("SELECT search_text FROM ticket WHERE id=70291"))
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "simwrk02_latest"
        )
        assert "worklog" not in inspect(connection).get_table_names()
        assert "ticket_link" in inspect(connection).get_table_names()
        assert any(
            index["name"] == "ft_ticket_search_text"
            for index in inspect(connection).get_indexes("ticket")
        )
