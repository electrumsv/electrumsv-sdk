from electrumsv_sdk.components import ComponentName
from electrumsv_sdk.utils import make_shell_script_for_component


def make_esv_custom_script(base_cmd, env_vars, component_args, esv_data_dir):
    """if cli args are supplied to electrumsv then it gives a "clean slate" (discarding the default
    configuration. (but ensures that the --dir and --restapi flags are set if not already)"""
    commandline_string = base_cmd
    additional_args = " ".join(component_args)
    commandline_string += " " + additional_args
    if "--dir" not in component_args:
        commandline_string += " " + f"--dir {esv_data_dir}"

    # so that polling works
    if "--restapi" not in component_args:
        commandline_string += " " + f"--restapi"

    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)


def make_esv_daemon_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" --portable --dir {esv_data_dir} "
        f"--regtest daemon -dapp restapi --v=debug --file-logging "
        f"--restapi --restapi-port={port} --server=127.0.0.1:51001:t --restapi-user rpcuser"
        f" --restapi-password= "
    )
    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)


def make_esv_gui_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" gui --regtest --restapi --restapi-port={port} "
        f"--v=debug --file-logging --server=127.0.0.1:51001:t --dir {esv_data_dir}"
    )
    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)
