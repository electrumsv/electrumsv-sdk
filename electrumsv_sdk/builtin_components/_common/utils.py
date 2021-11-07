import asyncio
import logging
import os
import pathlib


from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import get_directory_name


MODULE_DIR = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
SDK_POSTGRES_PORT: int = int(os.environ.get('SDK_POSTGRES_PORT', "5432"))
SDK_PORTABLE_MODE: int = int(os.environ.get('SDK_PORTABLE_MODE', "0"))
SDK_SKIP_POSTGRES_INIT: int = int(os.environ.get('SDK_SKIP_POSTGRES_INIT', "0"))

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)



def maybe_change_postgres_port() -> None:
    if SDK_POSTGRES_PORT != 5432:
        DBConnectionString = os.environ['ConnectionStrings__DBConnectionString']
        DBConnectionStringDDL = os.environ['ConnectionStrings__DBConnectionStringDDL']
        DBConnectionStringMaster = os.environ['ConnectionStrings__DBConnectionStringMaster']
        os.environ['ConnectionStrings__DBConnectionString'] = \
            DBConnectionString.replace("Port=5432", f"Port={SDK_POSTGRES_PORT}")
        os.environ['ConnectionStrings__DBConnectionStringDDL'] = \
            DBConnectionStringDDL.replace("Port=5432", f"Port={SDK_POSTGRES_PORT}")
        os.environ['ConnectionStrings__DBConnectionStringMaster'] = \
            DBConnectionStringMaster.replace("Port=5432", f"Port={SDK_POSTGRES_PORT}")


def download_and_init_postgres():
    config = Config()
    if SDK_PORTABLE_MODE == 1:
        postgres_install_path = config.DATADIR / "postgres"
        os.makedirs(postgres_install_path, exist_ok=True)

        # Set this environment variable before importing postgres script
        os.environ['SDK_POSTGRES_INSTALL_DIR'] = str(postgres_install_path)
        from .. import _postgres
        if not _postgres.check_extract_done():
            logger.info(
                f"downloading and extracting embedded postgres to {postgres_install_path}")
            _postgres.download_and_extract()

        # We do not initialise the db in the azure pipeline because there are issues with file
        # permissions
        if not _postgres.check_initdb_done() and SDK_SKIP_POSTGRES_INIT != 1:
            logger.info(f"running initdb for postgres port: {SDK_POSTGRES_PORT} "
                f"at: {postgres_install_path}")
            _postgres.initdb()


def reset_postgres():
    config = Config()
    if SDK_PORTABLE_MODE == 1:
        from .. import _postgres
        postgres_install_path = config.DATADIR / "postgres"
        if not asyncio.run(_postgres.check_running()):
            logger.info(f"resetting postgres at: {postgres_install_path}")
            _postgres.reset()


def start_postgres():
    config = Config()
    if SDK_PORTABLE_MODE == 1:
        from .. import _postgres
        postgres_install_path = config.DATADIR / "postgres"
        if not asyncio.run(_postgres.check_running()):
            logger.info(f"starting postgres port: {SDK_POSTGRES_PORT} at: {postgres_install_path}")
            _postgres.start()


def stop_postgres():
    config = Config()
    if SDK_PORTABLE_MODE == 1:
        from .. import _postgres
        postgres_install_path = config.DATADIR / "postgres"
        if not asyncio.run(_postgres.check_running()):
            logger.info(f"stopping postgres port: {SDK_POSTGRES_PORT} at: {postgres_install_path}")
            _postgres.stop()
