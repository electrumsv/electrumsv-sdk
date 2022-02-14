import logging
import sys

from electrumsv_sdk.components import ComponentStore

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('script')

NUM_COMPONENTS_STARTED = int(sys.argv[1])


class ComponentFailedToStartError(Exception):
    pass


component_store = ComponentStore()
component_state = component_store.get_status()

for component_name in component_state:
    if component_state[component_name]['component_state'] != 'Running':
        raise ComponentFailedToStartError(f"All components did not start sucessfully: "
            f"{component_state}")

    if len(component_state) != NUM_COMPONENTS_STARTED:
        raise ComponentFailedToStartError(f"Expected {NUM_COMPONENTS_STARTED} but only got: "
            f"{len(component_state)}")

logger.debug(f"Successfully started all components")
