import logging
from electrumsv_sdk.components import ComponentStore

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('script')


class ComponentFailedToStopError(Exception):
    pass


component_store = ComponentStore()
component_state = component_store.get_status()

for component_name in component_state:
    if component_state[component_name]['component_state'] != 'Stopped':
        raise ComponentFailedToStopError(f"All components did not stop successfully: "
            f"{component_state}")

logger.debug(f"Successfully stopped all components")
