import pprint
import logging
from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentStore, ComponentOptions, ComponentName, \
    ComponentState

from .constants import STATUS_MONITOR_GET_STATUS
from .handlers import Handlers
from .utils import cast_str_int_args_to_int

logger = logging.getLogger("runners")


class Controller:
    """Five main execution pathways (corresponding to 5 cli commands)"""

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.handlers = Handlers(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def start(self):
        logger.info("Starting component...")
        open(self.app_state.sdk_home_dir / "spawned_pids", 'w').close()

        # The status_monitor is a special-case component because it must always be running
        is_status_monitor_running = \
            self.app_state.is_component_running_http(STATUS_MONITOR_GET_STATUS, 2, 0.5,
            component_name=ComponentName.STATUS_MONITOR)

        if not is_status_monitor_running:
            component_module = self.app_state.import_plugin_component(ComponentName.STATUS_MONITOR)
            component_module.install(self.app_state)
            component_module.start(self.app_state)
            self.status_check(component_module)

        # All other component types
        if self.app_state.selected_component and \
                self.app_state.selected_component != ComponentName.STATUS_MONITOR:
            self.app_state.component_module.install(self.app_state)
            self.app_state.component_module.start(self.app_state)
            self.status_check()

        self.app_state.save_repo_paths()

        # no args implies (node, electrumx, electrumsv, whatsonchain)
        if not self.app_state.selected_component:
            self.app_state.run_command_current_shell("electrumsv-sdk start node")
            self.app_state.run_command_current_shell("electrumsv-sdk start electrumx")
            self.app_state.run_command_current_shell("electrumsv-sdk start electrumsv")
            self.app_state.run_command_current_shell("electrumsv-sdk start whatsonchain")

    def stop(self):
        """if stop_set is empty, all processes terminate."""
        # todo: make this granular enough to pick out instances of each component type

        self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = True
        if self.app_state.selected_stop_component:
            self.app_state.component_module.stop(self.app_state)

        # no args implies stop all (status_monitor, node, electrumx, electrumsv, whatsonchain)
        # call sdk recursively to achieve this (greatly simplifies code)
        if not self.app_state.selected_stop_component:
            self.app_state.run_command_current_shell("electrumsv-sdk stop node")
            self.app_state.run_command_current_shell("electrumsv-sdk stop electrumx")
            self.app_state.run_command_current_shell("electrumsv-sdk stop electrumsv")
            self.app_state.run_command_current_shell("electrumsv-sdk stop whatsonchain")
            self.app_state.run_command_current_shell("electrumsv-sdk stop status_monitor")
            logger.info(f"terminated: all")

    def reset(self):
        """No choice is given to the user at present - resets node, electrumx and electrumsv
        wallet. If stop_set is empty, all processes terminate."""
        self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = True
        component_id = self.app_state.global_cli_flags[ComponentOptions.ID]

        # reset by selected by --id flag or by <component_type>
        if component_id != "" or self.app_state.selected_component:
            self.app_state.component_module.reset(self.app_state)

        # no args (no --id or <component_type>) implies reset all (node, electrumx, electrumsv)
        elif component_id == "" and not self.app_state.selected_component:
            self.app_state.run_command_current_shell("electrumsv-sdk reset node")
            self.app_state.run_command_current_shell("electrumsv-sdk reset electrumx")
            self.app_state.run_command_current_shell("electrumsv-sdk reset electrumsv")

        # logging
        if component_id == "" and self.app_state.selected_component:
            logger.info(f"Reset of: {self.app_state.selected_component} complete.")
        elif component_id != "":
            logger.info(f"Reset of: {component_id} complete.")
        elif not self.app_state.selected_reset_component:
            logger.info(f"Reset of: all components complete")

        # cleanup
        self.app_state.run_command_current_shell("electrumsv-sdk stop status_monitor")

    def status_check(self, component_module=None):
        """The 'status_check()' entrypoint of the plugin must always run after the start()
        command.

        'status_check()' should return None, True or False (usually in response to polling for an
        http 200 OK response or 4XX/5XX error. However alternative litmus tests are customizable
        via the plugin.

        None type indicates that it was only run transiently (e.g. ElectrumSV's offline CLI mode)

        The status_monitor subsequently is updated with the status."""
        component_id = self.app_state.global_cli_flags[ComponentOptions.ID]
        component_module = component_module if component_module else \
            self.app_state.component_module
        component_name = component_module.COMPONENT_NAME

        # if --id flag or <component_type> are set and the
        if component_id != "" or component_name:
            is_running = component_module.status_check(self.app_state)

            if is_running is None:
                return

            if is_running is False:
                self.app_state.component_info.component_state = ComponentState.Failed
                logger.error(f"{component_name} failed to start")

            elif is_running is True:
                self.app_state.component_info.component_state = ComponentState.Running
                logger.debug(f"{component_name} online")
            self.app_state.component_store.update_status_file(self.app_state.component_info)
            self.app_state.status_monitor_client.update_status(self.app_state.component_info)
        else:
            raise Exception("neither component --id or component_name given")

    def node(self):
        """Essentially bitcoin-cli interface to RPC API that works 'out of the box' / zero config"""
        self.app_state.node_args = cast_str_int_args_to_int(self.app_state.node_args)
        assert electrumsv_node.is_running(), (
            "bitcoin node must be running to respond to rpc methods. "
            "try: electrumsv-sdk start --node"
        )

        if self.app_state.node_args[0] in ["--help", "-h"]:
            self.app_state.node_args[0] = "help"

        result = electrumsv_node.call_any(
            self.app_state.node_args[0], *self.app_state.node_args[1:]
        )
        logger.info(result.json()["result"])

    def status(self):
        status = self.component_store.get_status()
        pprint.pprint(status, indent=4)
