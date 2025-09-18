from __future__ import annotations
import os
from logging.config import fileConfig
from typing import Any, cast

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db import Base

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide access to target metadata

target_metadata = Base.metadata

# Override sqlalchemy.url from env if present
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section)
    if section is None:
        raise RuntimeError(
            "Missing config section for SQLAlchemy migrations: "
            f"{config.config_ini_section!r}"
        )

    section_config = cast(dict[str, Any], dict(section))

    connectable = engine_from_config(
        section_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()