# Release History

### Unreleased (see [master](https://github.com/electrumsv/electrumsv-sdk))
- Add `dpp-proxy` server to the SDK.
- Fixed a bug with the use of the `reset` command for the `merchant_api` component (when running the
SDK in standalone, portability mode).

### 0.0.42 (12/05/2022)
- Set the app version number in the terminal window title.
- Prevent all components from binding on `0.0.0.0` because it results in firewall permission
pop-ups. The SDK is now only intended for use on `RegTest` and so there is no reason to bind
on all interfaces like this.

### 0.0.41 (26/04/2022)
- Add `reference_server` component to the SDK. This server is designed to house all relevant 
LiteClient APIs as well as any other APIs specifically needed by ElectrumSV. It functions as a proxy
to multiple backend services in order to unify the full set of APIs as well as the authorization and
account model.
- Add `header_sv` component to the SDK (LiteClient component) - involves download of embedded 
Java RE.
- Set terminal window title with the name of the running component.

### 0.0.40 (12/11/2021)
- Add `simple_indexer` component to the SDK. This component is a very simplistic implementation of
the new set of indexer-backed APIs that ElectrumSV requires moving forward.

### 0.0.39 (10/11/2021)
- Upgrades to allow for usage of an embedded postgres instance on a non-default port.
- Added the reference implementation of Peer Channels as a new SDK component.
- Use Python3.10 as the recommended version.

### 0.0.37 (4/08/2021)
- Add comprehensive mypy static type checking to codebase
- Update mAPI version to 1.3.0
- Fix `stop` command on windows to perform `SIGINT` for all of `--inline`, '--background' and
`--new-terminal` modes of exectution.
- Set sockets to `SO_REUSEADDR` mode to prevent TCP cooldown from preventing rapid stop/start 
iterations of SDK components.
- Beginning to add portability features by allowing to specify an arbitrary `SDK_HOME` directory 
rather than the default os-specific home location. This is part of a new direction of creating
a fully standalone / bundled SDK CLI-Tool (where the user doesn't need to separately install 
anything).

### 0.0.36 (16/07/2021)
- Bump aiorpcX version to 0.22.1 as the minimum.

### 0.0.35 (6/05/2021)
- Python package versioning updates.

### 0.0.34 (6/05/2021)
- Increment to support of only Python3.9+. Drops official support for Python3.7 and Python3.8.
- docker-compose.yml updates.
- Python package versioning updates.

### 0.0.33 (9/02/2021)
- Documentation updates
- Changes to make the SDK usable as a python library (namely for use in CI/CD reorg functional 
testing scripts)
- Added a `--deterministic-seed` option for `ElectrumSV` to ease regtest functional testing efforts.
- Added `electrumsv-server` component which has a locally hosted interactive website for BIP270
invoicing and payments.
- Added broadcasting via mAPI for the `electrumsv-server`.

### 0.0.32 (15/01/2021)
- Pypi packaging fix (to ensure all relevant files are copied into the final bundle).

### 0.0.31 (14/01/2021)
- Update mAPI to ASP.NET Core-based version (from Go).
- Made significant new additions to online hosted documentation for each command and component.
- Added `BITCOIN_NETWORK` environment variable for `node`, `electrumx` and `electrumsv`.

### 0.0.30 (31/12/2020)
- Fix pypi markdown rendering of documentation. 

### 0.0.29 (31/12/2020)
- Bug fixes for conflicting python package versions across components (related to 
chardet and requests packages).
- Added `--testnet` and `--scaling-testnet` options for `electrumsv` component. 
`NOTE 2/06/2022`: The SDK is now strictly only intended for RegTest usage).
- Ensure multiple instances of the node do not conflict on the zmq port allocations.
- MacOS BigSur compatibility fixes. Uses OSAScript to launch new terminal windows.
- Remove http polling of subprocesses and instead check the exit returncode for status. This is
more reliable and works for any arbitrary plugin component.
- Fix graceful shutdown of all child processes via `signal.CTRL_C_EVENT` on windows.

### 0.0.28 (10/12/2020)
- Removed verbose help text as this information is better conveyed via the online documentation. 
The CLI should also now be self-describing.
- Added Dockerfiles for all components

### 0.0.27 (8/12/2020)
- Add --rpchost and --rpcport optional args to the `node` command to connect to a node's RPC
API that is not on localhost:18332.

### 0.0.26 (7/12/2020)
- Minor bug fixes

### 0.0.25 (7/12/2020)
- Removed intermediate step of generating shell scripts and instead directly launch applications
via `Popen`.
- Now shows node logs when running in a new terminal or inline

### 0.0.24 (20/11/2020)
- Added `install` command which decouples installation logic from `start` logic. This
results in faster startup times.
- General refactoring of codebase for organisation and readability.
- Added a "base" Docker image that installs all pre-requisites for running the SDK.

### 0.0.23 (19/11/2020)
- Allow configuration of ElectrumX via environment variables
- Allow change of node bind address (to 0.0.0.0) via environment variable to facilitate use within
docker.

### 0.0.22 (6/11/2020)
- Minor bug fix for merchant_api plugin

### 0.0.21 (6/11/2020)
- Added Merchant API v1.1.0
- Replaced curio-based status monitor with aiohttp framework (more
ubiquitous, production-ready framework).
- Added initial Sphinx documentation.
- Multiple minor bug fixes.

### 0.0.19 (19/10/2020)
- Large refactoring towards a plugin model for each component.
- Introduced a python virtual environment for insulating python
package dependencies from the system installation of python.

### 0.0.18 (22/09/2020)
- Add basic cross platform testing in Azure pipeline
(`install`, `start`, `stop`, `reset` command usage for each component)
- Add whatsonchain component (requires node.js installation)

### 0.0.17 (07/09/2020)
- Added `--background` flag for running components as background
processes. Required for azure pipeline.

### 0.0.16 (04/09/2020)
- Support multiple instances via the `--new` and `--id` flags.
- Allow passing arbitrary cli args to underlying `electrumsv` process
- `electrumsv-sdk start` with no args starts all components similarly
how `electrumsv-sdk stop` with no args stops all components.

### 0.0.15 (24/08/2020)
- Add Azure pipeline builds and pip wheels for hosting on pypi

### 0.0.14 (21/08/2020)
- Added a `status_monitor` component for real-time monitoring of 
the status of running servers (with the intention of later 
displaying this information in the `electrumsv-server`). Status can
be 'Running', 'Stopped', 'Failed'.
- Linux compatibility fixes (generally due to different file locations
and python pip behaviour requiring different command flags).
- `electrumsv-server` extended the BIP270 REST API

### 0.0.13 (24/07/2020)
- Move installation location to the user `LOCALAPPDATA` directory 
(platform dependent) in a directory called `ElectrumSV-SDK`.
- Fixed an issue where the pip wheel doesn't include all required 
source files.

### 0.0.11 (22/07/2020)
- Add `node` subcommand for interacting with the running bitcoin node
with RPC commands (standard bitcoin cli interface). Requires no configuration.

### 0.0.5 (21/07/2020)
- `electrumsv-server` now has an interactive website and the beginnings of 
a supporting REST API for `BIP270` payments.
- Add subcommands `start`, `stop`, `reset` to the `electrumsv-sdk` commandline tool.
- General Refactoring of code base file structure and minor bug fixing

### 0.0.3 (14/07/2020)
- Fixed an issue to do with the python pip install process
which should allow for running the `electrumsv-sdk` command
as a global system utility (on system PATH).

### 0.0.1 (14/07/2020)
- Basic functionality for automated installation and running of:
`node`, `electrumsv`, `electrumx` via the `electrumsv-sdk` 
commandline script.
- Initial exploratory code for the `electrumsv-server` with faux API
intended to eventually cover all of the public API requirements of ElectrumSV. 
The curio-based trinket framework was used for this initial implementation.
