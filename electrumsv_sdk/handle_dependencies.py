from electrumsv_sdk.config import load_config, Config


def validate_only_one_mode(parsed_args):
    modes_selected = []
    count_true = 0
    for cmd, mode in parsed_args.__dict__.items():
        if mode:
            modes_selected.append(cmd)
            count_true += 1
    if count_true not in [0, 1]:
        return False, modes_selected
    return True, modes_selected


class Handlers:
    """handlers check to see what is already installed compared to the cli inputs and
    if not installed and it is required will proceed to install the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo (just in case the user was using that repo for local
    development
    - would hate to destroy all of their hard work!

    No arg ("") will default to the 'official' github repo.
    """

    @classmethod
    def handle_electrumsv_sdk_args(cls, parsed_args):
        # print("handle_electrumsv_sdk_args")
        config: Config = load_config()

        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(
                f"You must only select ONE mode of operation. You selected '{modes_selected}'"
            )
            return

        if parsed_args.full_stack:
            config.required_dependencies_set.add(config.ELECTRUMSV)
            config.required_dependencies_set.add(config.ELECTRUMX)
            config.required_dependencies_set.add(config.ELECTRUMSV_NODE)

        if parsed_args.esv_ex_node:
            config.required_dependencies_set.add(config.ELECTRUMSV)
            config.required_dependencies_set.add(config.ELECTRUMX)
            config.required_dependencies_set.add(config.ELECTRUMSV_NODE)

        if parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        if parsed_args.ex_node:
            config.required_dependencies_set.add(config.ELECTRUMX)
            config.required_dependencies_set.add(config.ELECTRUMSV_NODE)

        if parsed_args.node:
            raise NotImplementedError("node mode is not supported yet")

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )

    @classmethod
    def handle_electrumsv_args(cls, parsed_args):
        # print("handle_electrumsv_args")
        config = load_config()
        if not config.ELECTRUMSV in config.required_dependencies_set:
            print(f"{config.ELECTRUMSV} not required")
            return
        print(f"{config.ELECTRUMSV} is required")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError(
                "loading dapps on the electrumsv daemon is not supported yet"
            )

        if parsed_args.repo == "":
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            print(f"-repo (default) = {parsed_args.repo}")
        elif parsed_args.repo.startswith("https://"):
            print(f"-repo (url) = {parsed_args.repo}")
        else:
            print(f"-repo (local) = {parsed_args.repo}")

        if parsed_args.branch == "":
            print("-default branch")
        else:
            print(f"-branch = {parsed_args.branch}")



    @classmethod
    def handle_electrumx_args(cls, parsed_args):
        # print("handle_electrumx_args")
        config = load_config()
        if not config.ELECTRUMX in config.required_dependencies_set:
            print(f"{config.ELECTRUMX} not required")
            return
        print(f"{config.ELECTRUMX} is required")

        if parsed_args.repo == "":
            parsed_args.repo = "https://github.com/kyuupichan/electrumx.git"
            print(f"-repo (default) = {parsed_args.repo}")
        elif parsed_args.repo.startswith("https://"):
            print(f"-repo (url) = {parsed_args.repo}")
        else:
            print(f"-repo (local) = {parsed_args.repo}")

        if parsed_args.branch == "":
            print("-default branch")
        else:
            print(f"-branch = {parsed_args.branch}")

    @classmethod
    def handle_electrumsv_node_args(cls, parsed_args):
        # print("handle_electrumsv_node_args")
        config = load_config()
        if not config.ELECTRUMSV_NODE in config.required_dependencies_set:
            print(f"{config.ELECTRUMSV_NODE} not required")
            return
        print(f"{config.ELECTRUMSV_NODE} is required")

        if parsed_args.repo == "":
            parsed_args.repo = "https://github.com/electrumsv/electrumsv_node.git"
            print(f"-repo (default) = {parsed_args.repo}")
        elif parsed_args.repo.startswith("https://"):
            print(f"-repo (url) = {parsed_args.repo}")
        else:
            print(f"-repo (local) = {parsed_args.repo}")

        if parsed_args.branch == "":
            print("-default branch")
        else:
            print(f"-branch = {parsed_args.branch}")


    @classmethod
    def handle_electrumsv_indexer_args(cls, parsed_args):
        # print("handle_electrumsv_indexer_args")
        config = load_config()
        if not config.ELECTRUMSV_INDEXER in config.required_dependencies_set:
            print(f"{config.ELECTRUMSV_INDEXER} not required")
            return

        print(f"{config.ELECTRUMSV_INDEXER} is required")
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

        if parsed_args.repo == "":
            parsed_args.repo = "????"
            print(f"-repo (default) = {parsed_args.repo}")
        elif parsed_args.repo.startswith("https://"):
            print(f"-repo (url) = {parsed_args.repo}")
        else:
            print(f"-repo (local) = {parsed_args.repo}")

        if parsed_args.branch == "":
            print("-default branch")
        else:
            print(f"-branch = {parsed_args.branch}")


def handle_dependencies():
    config = load_config()
    for cmd, parsed_args in config.subcmd_parsed_args_map.items():
        func = getattr(Handlers, "handle_" + cmd + "_args")
        func(parsed_args)
