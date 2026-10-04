import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# เพิ่ม Root Path ให้ Python มองเห็น app
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.base_class import Base

# Import Models ทั้งหมดเพื่อให้ Alembic เห็น Metadata
from app.db.models.user import User, Role, Team
from app.db.models.asset import Asset
from app.db.models.master_data import (
    Product, Module, ProblemType, Symptom, ServiceStage, TicketType, CauseCode, SolutionCode
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    # 1. ถ้ามี SQLALCHEMY_DATABASE_URI ให้ใช้ตัวนี้ก่อน
    if hasattr(settings, "SQLALCHEMY_DATABASE_URI") and settings.SQLALCHEMY_DATABASE_URI:
        return str(settings.SQLALCHEMY_DATABASE_URI)
    
    # 2. ดึงค่าตัวแปรโดยใช้ getattr เพื่อกัน AttributeError
    user = getattr(settings, "MARIADB_USER", getattr(settings, "DB_USER", "root"))
    password = getattr(settings, "MARIADB_PASSWORD", getattr(settings, "DB_PASSWORD", ""))
    host = getattr(settings, "MARIADB_HOST", getattr(settings, "DB_HOST", getattr(settings, "MARIADB_SERVER", "localhost")))
    port = getattr(settings, "MARIADB_PORT", getattr(settings, "DB_PORT", 3306))
    db_name = getattr(settings, "MARIADB_DATABASE", getattr(settings, "DB_NAME", getattr(settings, "MARIADB_DB", "isms_db")))
    
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
