import asyncio
import logging

import aiorpcx

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


async def is_electrumx_running():
    for sleep_time in (1, 2, 3):
        try:
            logger.debug("Polling electrumx...")
            async with aiorpcx.connect_rs(host="127.0.0.1", port=51001) as session:
                result = await session.send_request("server.version")
                if result[1] == "1.4":
                    return True
        except Exception as e:
            pass

        await asyncio.sleep(sleep_time)
    return False
