"""
See exe-config/.env for hard-coded settings

Pre-requisites for this plugin to work are:
- postgres running (e.g. via a docker container or a system installation - this is up to the user)
- an admin user=mapimaster and password=mapimasterpass

This script will create:
- restricted access user: 'merchant' with password='merchant'
- the database 'merchant_gateway' with owner='merchant'

In Azure, psql cli tool is not working for me to perform these functions so
this is the workaround.
"""
import asyncio
import logging
import sys

import asyncpg

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


async def pg_connect():
    pg_conn = await asyncpg.connect(
        user="mapimaster",  # usually would be 'postgres'
        host="127.0.0.1",
        port=5432,
        password="mapimasterpass",  # usually would be 'postgres'
        database="postgres",
    )
    return pg_conn


async def create_user_if_not_exists(pg_conn: asyncpg.Connection):
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'merchant';""")
    if not result:
        logger.debug("creating user: 'merchant'")
        await pg_conn.execute("""
                DROP ROLE IF EXISTS merchant;

                CREATE ROLE merchant LOGIN
                  PASSWORD 'merchant'
                  NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
            """)


async def create_db_if_not_exists(pg_conn: asyncpg.Connection):
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_database WHERE datname = 'merchant_gateway'"""
    )
    if not result:
        logger.debug("creating merchant_gateway database")
        await pg_conn.execute(
            """
            CREATE DATABASE merchant_gateway
              WITH OWNER = merchant
              ENCODING = 'UTF8'
              TABLESPACE = pg_default
              CONNECTION LIMIT = -1;"""
        )


async def main_task():
    pg_conn = None
    try:
        pg_conn = await pg_connect()
        await create_user_if_not_exists(pg_conn)
        await create_db_if_not_exists(pg_conn)
    except Exception:
        logger.exception("postgres database check failed - please see documentation to configure "
            "postgres")
        sys.exit(1)
    finally:
        if pg_conn:
            await pg_conn.close()


def check_postgres_db():
    asyncio.run(main_task())
