import json
import logging
import subprocess

from electrumsv_node import electrumsv_node


logger = logging.getLogger("stoppers")


class Stoppers:

    def __init__(self, app_state):
        self.app_state = app_state

    def stop_node(self):
        electrumsv_node.stop()

    def stop_status_monitor(self):
        raise NotImplementedError  # kill signal via subprocess

    def stop_electrumsv(self):
        raise NotImplementedError  # kill signal via subprocess

    def stop_electrumx(self):
        raise NotImplementedError  # kill signal via subprocess

    def stop_indexer(self):
        raise NotImplementedError  # kill signal via subprocess

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

        # self.stop_status_monitor()
        print("stack terminated")
