from electrumsv_sdk.app import load_config

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
    """handlers check to see what is already installed compared to the cli inputs versus what
    dependencies are lacking and if not installed and required will proceed to install
    the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo (just in case the user was using that repo for local
    development
    - would hate to destroy all of their hard work!

    No arg ("") will default to the 'official' github repo.
    """

    @classmethod
    def handle_electrumsv_sdk_args(cls, parsed_args):
        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        print('handle_electrumsv_sdk_args')
        if parsed_args.full_stack:
            raise NotImplementedError("full_stack mode is not supported yet")

        if parsed_args.esv_ex_node:
            raise NotImplementedError("esv_ex_node mode is not supported yet")

        if parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        if parsed_args.ex_node:
            raise NotImplementedError("ex_node mode is not supported yet")

        if parsed_args.node:
            raise NotImplementedError("node mode is not supported yet")

        if parsed_args.extapp_path != '':
            raise NotImplementedError("loading extapps on the electrumsv daemon is "
                "not supported yet")

    @classmethod
    def handle_electrumsv_args(cls, parsed_args):
        print('handle_electrumsv_args')

        # dapp_path
        if parsed_args.dapp_path != '':
            raise NotImplementedError("loading dapps on the electrumsv daemon is not "
                "supported yet")

        if parsed_args.repo == '':
            print("default repo for electrumsv")

        if parsed_args.branch == '':
            print("default branch for electrumsv")

    @classmethod
    def handle_electrumx_args(cls, parsed_args):
        print('handle_electrumx_args')

        if parsed_args.repo == '':
            print("default repo for electrumx")

        if parsed_args.branch == '':
            print("default branch for electrumx")

    @classmethod
    def handle_electrumsv_indexer_args(cls, parsed_args):
        print('handle_electrumsv_indexer_args')

        if parsed_args.repo == '':
            print("default repo for electrumsv indexer")

        if parsed_args.branch == '':
            print("default branch for electrumsv indexer")

    @classmethod
    def handle_electrumsv_node_args(cls, parsed_args):
        print('handle_electrumsv_node_args')

        if parsed_args.repo == '':
            print("default repo for electrumsv node")

        if parsed_args.branch == '':
            print("default branch for electrumsv node")

def handle_dependencies():
    config = load_config()
    for cmd, parsed_args in config.subcmd_parsed_args_map.items():
        func = getattr(Handlers, "handle_" + cmd + "_args")
        func(parsed_args)
