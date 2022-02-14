"""
See exe-cli_inputs/.env for hard-coded settings

Pre-requisites for this plugin to work are:
- postgres running (e.g. via a docker container or a system installation - this is up to the user)
- an admin user=postgres and password=postgres

This script will create:
- restricted access users: 'channels_crud' & channelsddl with password='channels'
- the database 'channels' with owner='channels_crud'

In Azure, psql cli tool is not working for me to perform these functions so
this is the workaround.
"""
import asyncio
import logging
import os
import sys

import asyncpg

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)

SDK_POSTGRES_PORT = os.environ.get('SDK_POSTGRES_PORT', 5432)


async def pg_connect(db_name='postgres') -> asyncpg.connection.Connection:
    pg_conn = await asyncpg.connect(
        user="channels",  # usually would be 'postgres'
        host="127.0.0.1",
        port=SDK_POSTGRES_PORT,
        password="channels",  # usually would be 'postgres'
        database=db_name,
    )
    return pg_conn


async def drop_db_if_exists() -> None:
    pg_conn = None
    try:
        pg_conn = await pg_connect(db_name='postgres')  # initial connection

        # This overcomes an issue where there may still be outstanding sessions trying to access the
        # 'merchant_gateway' database.
        # https://medium.com/@p.edwin200294/postgresql-drop-database-detail-there-is-1-other-session-using-the-database-c014056b2a29
        await pg_conn.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'channels';""")
        await pg_conn.execute("""DROP DATABASE IF EXISTS channels""")
        await pg_conn.close()
    except Exception:
        logger.exception("postgres database check failed - please see documentation to configure "
            "postgres")
        raise
    finally:
        if pg_conn:
            await pg_conn.close()


def drop_db_on_install() -> None:
    asyncio.run(drop_db_if_exists())


async def create_user_if_not_exists(pg_conn: asyncpg.Connection) -> None:
    # result = await pg_conn.fetchrow(
    #     """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'channels_crud';""")
    # if not result:
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'channels_crud';""")
    if not result:
        logger.debug("creating user: 'channels_crud'")
        await pg_conn.execute("""
                CREATE ROLE "channels_crud" LOGIN
                    PASSWORD 'channels'
                    NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
            """)

    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'channelsddl';""")
    if not result:
        logger.debug("creating user: 'channelsddl'")
        await pg_conn.execute("""
            DROP ROLE IF EXISTS channelsddl;

            CREATE ROLE channelsddl LOGIN
                PASSWORD 'channels'
                NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
            
            ALTER SCHEMA public OWNER TO channelsddl;
            """)


async def create_db_if_not_exists(pg_conn: asyncpg.Connection) -> None:
    result = await pg_conn.fetchrow(
        """SELECT * FROM pg_database WHERE datname = 'channels'"""
    )
    if not result:
        logger.debug("creating channels database")
        await pg_conn.execute(
            """
            CREATE DATABASE channels
              WITH OWNER = postgres
              ENCODING = 'UTF8'
              TABLESPACE = pg_default
              CONNECTION LIMIT = -1;"""
        )


async def main_task() -> None:
    pg_conn = None
    try:
        pg_conn = await pg_connect(db_name='postgres')  # initial connection
        await create_db_if_not_exists(pg_conn)  # create 'channels' db
        await pg_conn.close()

        pg_conn = await pg_connect(db_name='channels')
        await create_user_if_not_exists(pg_conn)
    except Exception:
        logger.exception("postgres database check failed - please see documentation to configure "
            "postgres")
        sys.exit(1)
    finally:
        if pg_conn:
            await pg_conn.close()


def check_postgres_db() -> None:
    asyncio.run(main_task())
