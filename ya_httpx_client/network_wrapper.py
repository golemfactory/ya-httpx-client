import asyncio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Optional
    from yapapi.network import Network


class NetworkWrapper:
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self._network: 'Optional[Network]' = None
        self._network_state_lock = asyncio.Lock()

    async def network(self):
        async with self._network_state_lock:
            if self._network is None:
                self._network = await self.service_manager.create_network("192.168.0.1/24")
        return self._network

    async def remove_network(self):
        async with self._network_state_lock:
            if self._network is not None:
                await self._network.remove()
            self._network = None
