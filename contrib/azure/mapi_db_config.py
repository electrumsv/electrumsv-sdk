"""
Create superuser mapimaster with password=mapimasterpass for default postgres install
"""
import asyncio
import os

import asyncpg
import logging


logger = logging.getLogger('mapi-db-config')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', 5432)


async def pg_connect():
    pg_conn = await asyncpg.connect(
        user="postgres",
        host="127.0.0.1",
        port=POSTGRES_PORT,
        password='postgres',
        database="postgres",
    )
    return pg_conn


async def create_user_if_not_exists(pg_conn: asyncpg.Connection):
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'mapimaster';""")
    if not result:
        logger.info("creating user: 'mapimaster'")
        await pg_conn.execute("""
                DROP ROLE IF EXISTS mapimaster;

                CREATE ROLE mapimaster WITH
                    LOGIN
                    SUPERUSER
                    INHERIT
                    CREATEDB
                    CREATEROLE
                    NOREPLICATION
                    ENCRYPTED PASSWORD 'md5cfc51c7943d1a92b4d440f5e7d69d3b9';
            """)


async def create_db_if_not_exists(pg_conn: asyncpg.Connection):
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


async def main_task():
    pg_conn = None
    try:
        pg_conn = await pg_connect()
        await create_user_if_not_exists(pg_conn)
    except Exception:
        logger.exception("postgres database check failed")
    finally:
        if pg_conn:
            await pg_conn.close()


def check_postgres_db():
    asyncio.run(main_task())


if __name__ == '__main__':
    check_postgres_db()
