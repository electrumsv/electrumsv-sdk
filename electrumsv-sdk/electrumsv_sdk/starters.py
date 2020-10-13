import asyncio
import logging
import subprocess
import sys
import time
import os

import aiorpcx
import requests
from electrumsv_node import electrumsv_node

from .utils import trace_pid, trace_processes_for_cmd
from .constants import STATUS_MONITOR_API, DEFAULT_ID_ELECTRUMSV, DEFAULT_ID_ELECTRUMX, \
    DEFAULT_ID_NODE, DEFAULT_ID_STATUS, DEFAULT_ID_WOC
from .status_monitor_client import StatusMonitorClient

from .components import Component, ComponentName, ComponentType, ComponentState, ComponentStore, \
    ComponentOptions

logger = logging.getLogger("starters")
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class ComponentLaunchFailedError(Exception):
    pass


class Starters:
    def __init__(self, app_state):
        self.app_state = app_state
        self.component_store = ComponentStore(self.app_state)
        self.status_monitor_client = StatusMonitorClient(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def spawn_process(self, command):
        if self.app_state.start_options[ComponentOptions.BACKGROUND]:
            return self.spawn_in_background(command)
        else:
            return self.spawn_in_new_console(command)

    def spawn_in_background(self, command):
        if sys.platform in ('linux', 'darwin'):
            len_processes_before = len(trace_processes_for_cmd(command))

            process = subprocess.Popen(f"nohup {command} &", shell=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            process.wait()
            time.sleep(1)  # allow brief time window for process to fail at startup

            len_processes_after = len(trace_processes_for_cmd(command))
            if len_processes_before == len_processes_after:
                logger.error(f"failed to launch command: {command}")
                raise ComponentLaunchFailedError()

            process_handle = trace_pid(command)
            return process_handle
        elif sys.platform == 'win32':
            logger.info(
                "Running as a background process (without a console window) is not supported "
                "on windows, spawning in a new console window")
            process_handle = subprocess.Popen(
                f"{command}", creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            return process_handle

    def spawn_in_new_console(self, command):
        if sys.platform in ('linux', 'darwin'):
            len_processes_before = len(trace_processes_for_cmd(command))

            # todo gnome-terminal part will not work cross-platform for spawning new terminals
            process = subprocess.Popen(f"gnome-terminal -- {command}", shell=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            time.sleep(1)  # allow brief time window for process to fail at startup

            len_processes_after = len(trace_processes_for_cmd(command))
            if len_processes_before == len_processes_after:
                logger.error(f"failed to launch command: {command}. On linux cloud servers try "
                             f"using the --background flag e.g. electrumsv-sdk start "
                             f"--background node.")
                raise ComponentLaunchFailedError()

            process_handle = trace_pid(command)
            return process_handle

        elif sys.platform == 'win32':
            process_handle = subprocess.Popen(
                f"{command}", creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            return process_handle

    async def is_electrumx_running(self):
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

    def is_electrumsv_running(self):
        for sleep_time in (3, 3, 3, 3, 3):
            try:
                logger.debug("Polling electrumsv...")
                result = requests.get("http://127.0.0.1:9999/")
                result.raise_for_status()
                assert result.json()["status"] == "success"
                return True
            except Exception as e:
                pass

            time.sleep(sleep_time)
        return False

    def is_status_monitor_running(self) -> bool:
        for sleep_time in (0.5, 0.5, 0.5):
            try:
                result = requests.get(STATUS_MONITOR_API + "/get_status", timeout=0.5)
                result.raise_for_status()
                return True
            except requests.exceptions.ConnectionError as e:
                pass

            time.sleep(sleep_time)
        return False

    def start_node(self):
        process_pid = electrumsv_node.start()

        id = self.app_state.start_options[ComponentOptions.ID]
        if not id:
            id = DEFAULT_ID_NODE

        component = Component(
            id=id,
            pid=process_pid,
            process_type=ComponentType.NODE,
            endpoint="http://127.0.0.1:18332",
            component_state=ComponentState.NONE,
            location=None,
            metadata={},
            logging_path=None,
        )
        if not electrumsv_node.is_node_running():
            component.component_state = ComponentState.Failed
            logger.error("bitcoin daemon failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("Bitcoin daemon online")

        self.component_store.update_status_file(component)
        self.status_monitor_client.update_status(component)

        # process handle not returned because node is stopped via rpc

    def start_electrumx(self):
        logger.debug(f"Starting RegTest electrumx server...")
        script_path = self.component_store.derive_shell_script_path(ComponentName.ELECTRUMX)
        process = self.spawn_process(script_path)

        id = self.app_state.start_options[ComponentOptions.ID]
        if not id:
            id = DEFAULT_ID_ELECTRUMX

        component = Component(
            id=id,
            pid=process.pid,
            process_type=ComponentType.ELECTRUMX,
            endpoint="http://127.0.0.1:51001",
            component_state=ComponentState.NONE,
            location=str(self.app_state.electrumx_dir),
            metadata={"data_dir": str(self.app_state.electrumx_data_dir)},
            logging_path=None,
        )

        is_running = asyncio.run(self.is_electrumx_running())
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("Electrumx server failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("Electrumx online")
        time.sleep(3)
        self.component_store.update_status_file(component)
        self.status_monitor_client.update_status(component)
        return process

    def init_electrumsv_wallet_dir(self):
        os.makedirs(self.app_state.electrumsv_regtest_wallets_dir, exist_ok=True)

    def esv_check_node_and_electrumx_running(self):
        if not electrumsv_node.is_running():
            logger.debug("Electrumsv in RegTest mode requires a bitcoin node to be running... "
                         "failed to connect")
            sys.exit()

        is_running = asyncio.run(self.is_electrumx_running())
        if not is_running:
            logger.debug("Electrumsv in RegTest mode requires electrumx to be running... "
                         "failed to connect")

    def start_electrumsv(self, is_first_run=False):
        """Todo - this currently uses ugly hacks with starting and stopping the ESV wallet
         in order to:
        1) generate the config files (so that it can be directly edited) - would be obviated by
        fixing this: https://github.com/electrumsv/electrumsv/issues/111
        2) newly created wallet doesn't seem to be fully useable until after stopping the daemon."""
        logger.debug(f"Starting RegTest electrumsv daemon...")
        # Option (1) Only using offline cli interface to electrumsv
        if len(self.app_state.component_args) != 0:
            if self.app_state.component_args[0] in ['create_wallet', 'create_account', '--help']:
                return

        # Option (2) Running daemon or gui proper
        self.esv_check_node_and_electrumx_running()
        self.init_electrumsv_wallet_dir()

        script_path = self.component_store.derive_shell_script_path(ComponentName.ELECTRUMSV)
        process = self.spawn_process(script_path)
        if is_first_run:
            self.app_state.resetters.reset_electrumsv_wallet()  # create first-time wallet

            if sys.platform in ("linux", "darwin"):
                subprocess.run(f"pkill -P {process.pid}", shell=True)
            elif sys.platform == "win32":
                subprocess.run(f"taskkill.exe /PID {process.pid} /T /F", check=True)
            return self.start_electrumsv(is_first_run=False)

        id = self.app_state.start_options[ComponentOptions.ID]
        if not id:
            id = DEFAULT_ID_ELECTRUMSV

        logging_path = self.app_state.electrumsv_data_dir.joinpath("logs")

        component = Component(
            id=id,
            pid=process.pid,
            process_type=ComponentType.ELECTRUMSV,
            endpoint="http://127.0.0.1:9999",
            component_state=ComponentState.NONE,
            location=str(self.app_state.electrumsv_regtest_dir),
            metadata={"config": str(self.app_state.electrumsv_regtest_config_path)},
            logging_path=str(logging_path),
        )

        is_running = self.is_electrumsv_running()
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("Electrumsv failed to start")
            sys.exit(1)
        else:
            component.component_state = ComponentState.Running
            logger.debug("Electrumsv online")

        self.component_store.update_status_file(component)
        self.status_monitor_client.update_status(component)
        return process

    def start_status_monitor(self):
        logger.debug(f"Starting status monitor daemon...")
        try:
            script_path = self.component_store.derive_shell_script_path(
                ComponentName.STATUS_MONITOR)
            process = self.spawn_process(script_path)
        except ComponentLaunchFailedError:
            log_files = os.listdir(self.app_state.status_monitor_logging_path)
            log_files.sort(reverse=True)  # get latest log file at index 0
            logger.debug(f"see {self.app_state.status_monitor_logging_path.joinpath(log_files[0])} "
                         f"for details")
            sys.exit(1)

        id = self.app_state.start_options[ComponentOptions.ID]
        if not id:
            id = DEFAULT_ID_STATUS

        component = Component(
            id=id,
            pid=process.pid,
            process_type=ComponentType.STATUS_MONITOR,
            endpoint="http://127.0.0.1:api/status",
            component_state=ComponentState.Running,
            location=str(self.app_state.status_monitor_dir),
            metadata={},
            logging_path=None,
        )

        is_running = self.is_status_monitor_running()
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("Status_monitor failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("Status_monitor online")
        self.component_store.update_status_file(component)
        return process

    def start_whatsonchain(self):
        if not self.check_node_for_woc():
            sys.exit(1)

        logger.debug(f"Starting whatsonchain daemon...")
        script_path = self.component_store.derive_shell_script_path(ComponentName.WHATSONCHAIN)
        process = self.spawn_process(script_path)

        id = self.app_state.start_options[ComponentOptions.ID]
        if not id:
            id = DEFAULT_ID_WOC

        component = Component(
            id=id,
            pid=process.pid,
            process_type=ComponentType.WOC,
            endpoint="http://127.0.0.1:api/status",
            component_state=ComponentState.Running,
            location=str(self.app_state.woc_dir),
            metadata={},
            logging_path=None,
        )

        is_running = self.is_woc_server_running()
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("woc server failed to start")
            sys.exit(1)
        else:
            component.component_state = ComponentState.Running
            logger.debug("Whatsonchain server online")
        self.component_store.update_status_file(component)
        self.status_monitor_client.update_status(component)
        return process

    def is_woc_server_running(self):
        for timeout in (3, 3, 3, 3, 3):
            try:
                result = requests.get("http://localhost:3002", timeout=1.0)
                result.raise_for_status()
                if result.status_code == 200:
                    return True
            except Exception as e:
                time.sleep(timeout)
                continue
        return False

    def check_node_for_woc(self):
        if not electrumsv_node.is_running():
            return False

        result = electrumsv_node.call_any("getinfo")
        block_height = result.json()['result']['blocks']
        if block_height == 0:
            logger.error(f"Block height=0. "
                f"The Whatsonchain explorer requires at least 1 block to be mined. Hint: try: "
                f"'electrumsv-sdk node generate 1'")
            return False
        return True
