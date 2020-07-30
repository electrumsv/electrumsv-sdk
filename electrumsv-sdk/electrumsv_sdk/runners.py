import asyncio
import aiorpcx
import json
import logging
import requests
import subprocess
import sys
import time
from electrumsv_node import electrumsv_node

from .components import Component, ComponentType, ComponentName, ComponentState

logger = logging.getLogger("runners")

class Runners:

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state

    async def is_electrumx_running(self):
        for sleep_time in (1, 2, 3):
            try:
                logger.debug("polling electrumx...")
                async with aiorpcx.connect_rs(host="127.0.0.1", port=51001) as session:
                    result = await session.send_request("server.version")
                    if result[1] == "1.4":
                        return True
            except Exception as e:
                pass

            await asyncio.sleep(sleep_time)
        return False

    def is_electrumsv_running(self):
        for sleep_time in (3, 3, 3):
            try:
                logger.debug("polling electrumsv...")
                result = requests.get("http://127.0.0.1:9999/")
                result.raise_for_status()
                assert result.json()['status'] == 'success'
                return True
            except Exception as e:
                pass

            time.sleep(sleep_time)
        return False

    def start_node(self):
        process = electrumsv_node.start()

        component = Component(
            pid=process.pid,
            process_name=ComponentName.NODE,
            process_type=ComponentType.NODE,
            endpoint="http://127.0.0.1:18332",
            component_state=ComponentState.NONE,
            location=None,
            metadata={},
            logging_path=None,
        )
        logger.debug("polling bitcoin daemon...")
        if not electrumsv_node.is_running():
            component.component_state = ComponentState.Failed
            logger.error("bitcoin daemon failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("bitcoin daemon online")
        self.app_state.update_status(component)

        # process handle not returned because node is stopped via rpc

    def run_electrumx_server(self):
        logger.debug(f"starting RegTest electrumx server...")
        if sys.platform == "win32":
            electrumx_server_script = self.app_state.run_scripts_dir.joinpath("electrumx.bat")
        else:
            electrumx_server_script = self.app_state.run_scripts_dir.joinpath("electrumx.sh")

        process = subprocess.Popen(
            f"{electrumx_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        component = Component(
            pid=process.pid,
            process_name=ComponentName.ELECTRUMX,
            process_type=ComponentType.ELECTRUMX,
            endpoint="http://127.0.0.1:51001",
            component_state=ComponentState.NONE,
            location=self.app_state.electrumx_dir.__str__(),
            metadata={"data_dir": self.app_state.electrumx_data_dir.__str__()},
            logging_path=None,
        )

        is_running = asyncio.run(self.is_electrumx_running())
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("electrumx server failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("electrumx online")
        self.app_state.update_status(component)
        return process

    def disable_rest_api_authentication(self):
        path_to_config = self.app_state.electrumsv_regtest_config_dir.__str__()

        with open(path_to_config, "r") as f:
            config = json.load(f)
            config["rpcpassword"] = ""
            config["rpcuser"] = "user"

        with open(path_to_config, "w") as f:
            f.write(json.dumps(config, indent=4))

    def start_and_stop_ESV(self, electrumsv_server_script):
        # Ugly hack (first time run through need to start then stop ESV wallet to make config files)
        logger.debug(
            "starting RegTest electrumsv daemon for the first time - initializing wallet - "
            "standby..."
        )
        process = subprocess.Popen(
            f"{electrumsv_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        time.sleep(7)
        subprocess.run(f"taskkill.exe /PID {process.pid} /T /F")

    def run_electrumsv_daemon(self, is_first_run=False):
        """Todo - this currently uses ugly hacks with starting and stopping the ESV wallet in order to:
        1) generate the config files (so that it can be directly edited) - would be obviated by
        fixing this: https://github.com/electrumsv/electrumsv/issues/111
        2) newly created wallet doesn't seem to be fully useable until after stopping the daemon."""
        if sys.platform == "win32":
            electrumsv_server_script = self.app_state.run_scripts_dir.joinpath("electrumsv.bat")
        else:
            electrumsv_server_script = self.app_state.run_scripts_dir.joinpath("electrumsv.sh")

        try:
            self.disable_rest_api_authentication()
        except FileNotFoundError:  # is_first_run = True
            self.start_and_stop_ESV(electrumsv_server_script)  # generates config json file
            self.disable_rest_api_authentication()  # now this will work
            return self.run_electrumsv_daemon(is_first_run=True)

        logger.debug(f"starting RegTest electrumsv daemon...")
        process = subprocess.Popen(
            f"{electrumsv_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        if is_first_run:
            time.sleep(7)
            self.app_state.resetters.reset_electrumsv_wallet()  # create first-time wallet
            time.sleep(1)
            subprocess.run(f"taskkill.exe /PID {process.pid} /T /F", check=True)
            return self.run_electrumsv_daemon(is_first_run=False)

        component = Component(
            pid=process.pid,
            process_name=ComponentName.ELECTRUMSV,
            process_type=ComponentType.ELECTRUMSV,
            endpoint="http://127.0.0.1:9999",
            component_state=ComponentState.NONE,
            location=self.app_state.electrumsv_regtest_dir.__str__(),
            metadata={"config": self.app_state.electrumsv_regtest_config_dir.__str__()},
            logging_path=self.app_state.electrumsv_data_dir.joinpath("logs").__str__(),
        )

        is_running = self.is_electrumsv_running()
        if not is_running:
            component.component_state = ComponentState.Failed
            logger.error("electrumsv failed to start")
        else:
            component.component_state = ComponentState.Running
            logger.debug("electrumsv online")
        self.app_state.update_status(component)
        return process

    def start(self):
        print()
        print()
        print("running stack...")

        procs = []
        self.start_status_server()

        if self.app_state.NODE in self.app_state.required_dependencies_set:
            self.start_node()
            time.sleep(2)

        if self.app_state.ELECTRUMX in self.app_state.required_dependencies_set:
            electrumx_process = self.run_electrumx_server()
            procs.append(electrumx_process.pid)

        if self.app_state.ELECTRUMSV in self.app_state.required_dependencies_set:
            esv_process = self.run_electrumsv_daemon()
            procs.append(esv_process.pid)

        with open(self.app_state.proc_ids_path, "w") as f:
            f.write(json.dumps(procs))

        self.app_state.save_repo_paths()

    def stop(self):
        # Todo - need to make this more specific and know at all times which pid belongs
        #  to which server so servers can be selectively killed from the command-line

        with open(self.app_state.proc_ids_path, "r") as f:
            procs = json.loads(f.read())

        self.stop_node()

        if len(procs) != 0:
            for proc_id in procs:
                subprocess.run(f"taskkill.exe /PID {proc_id} /T /F")

        with open(self.app_state.proc_ids_path, "w") as f:
            f.write(json.dumps({}))

        self.stop_status_server()
        print("stack terminated")

    def node(self):
        def cast_str_int_args_to_int():
            int_indices = []
            for index, arg in enumerate(self.app_state.node_args):
                if arg.isdigit():
                    int_indices.append(index)

            for i in int_indices:
                self.app_state.node_args[i] = int(self.app_state.node_args[i])

        cast_str_int_args_to_int()
        assert electrumsv_node.is_running(), (
            "bitcoin node must be running to respond to rpc methods. "
            "try: electrumsv-sdk start --node"
        )

        if self.app_state.node_args[0] in ["--help", "-h"]:
            self.app_state.node_args[0] = "help"

        result = electrumsv_node.call_any(self.app_state.node_args[0], *self.app_state.node_args[1:])
        print(result.json()["result"])

    def status(self):
        status = self.app_state.get_status()
        logger.debug(f"status={status}")

    def reset(self):
        self.app_state.load_repo_paths()
        self.app_state.resetters.reset_node()
        self.app_state.resetters.reset_electrumx()

        self.app_state.required_dependencies_set.add(self.app_state.ELECTRUMSV_NODE)
        self.app_state.required_dependencies_set.add(self.app_state.ELECTRUMX)
        self.app_state.required_dependencies_set.add(self.app_state.ELECTRUMSV)
        self.start()
        logger.debug("allowing time for the electrumsv daemon to boot up - standby...")
        time.sleep(7)
        self.app_state.resetters.reset_electrumsv_wallet()
        self.stop()

    def stop_node(self):
        electrumsv_node.stop()

    def start_status_server(self):
        self.app_state.status_server.start()

    def stop_status_server(self):
        self.app_state.status_server_queue.put(None)
