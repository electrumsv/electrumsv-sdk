"""
Create superuser channels with password=channels for default postgres install
"""
import asyncio
import os
from typing import Optional

import asyncpg
import logging


logger = logging.getLogger('peer-channels-config')
SDK_POSTGRES_PORT = os.environ.get('SDK_POSTGRES_PORT', 5432)
logger.debug(f"Using postgres port: {SDK_POSTGRES_PORT}")


async def pg_connect() -> None:
    pg_conn = await asyncpg.connect(
        user="postgres",
        host="127.0.0.1",
        port=SDK_POSTGRES_PORT,
        password='postgres',
        database="postgres",
    )
    return pg_conn


async def create_user_if_not_exists(pg_conn: asyncpg.Connection) -> None:
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'channels';""")
    if not result:
        logger.info("creating user: 'channels'")
        await pg_conn.execute("""
                DROP ROLE IF EXISTS channels;

                CREATE ROLE channels WITH
                    LOGIN
                    SUPERUSER
                    INHERIT
                    CREATEDB
                    CREATEROLE
                    NOREPLICATION
                    PASSWORD 'channels';
            """)


async def create_db_if_not_exists(pg_conn: asyncpg.Connection) -> None:
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_database WHERE datname = 'postgres'"""
    )
    if not result:
        logger.info("creating postgres database")
        await pg_conn.execute(
            """
            CREATE DATABASE postgres
              WITH OWNER = postgres
              ENCODING = 'UTF8'
              TABLESPACE = pg_default
              CONNECTION LIMIT = -1;"""
        )


async def main_task() -> None:
    pg_conn: Optional[asyncpg.Connection] = None
    try:
        pg_conn = await pg_connect()
        await create_user_if_not_exists(pg_conn)
    except Exception:
        logger.exception("postgres database check failed")
    finally:
        if pg_conn:
            await pg_conn.close()


def check_postgres_db() -> None:
    asyncio.run(main_task())


if __name__ == '__main__':
    check_postgres_db()
