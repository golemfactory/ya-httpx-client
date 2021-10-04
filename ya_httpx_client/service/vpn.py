import aiohttp
from yapapi.payload import vm

from .service_base import AbstractServiceBase
from ..serializable_request import Response


class VPNService(AbstractServiceBase):
    REQUIRED_CAPABILITIES = [vm.VM_CAPS_VPN]

    async def run(self):
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            res = await self._handle_request_with_504_guard(req)
            fut.set_result(res)

        #   We never get here, but `run` is supposed to be a generator, so we need a yield
        yield

    async def _handle_request_with_504_guard(self, req):
        max_attempts = 3
        for _ in range(max_attempts):
            try:
                return await self._handle_request(req)
            except aiohttp.WSServerHandshakeError:
                pass
        raise Exception(f"Provider {self.provider_name} had WSServerHandshakeError {max_attempts} times in a row")

    async def _handle_request(self, req):
        async with aiohttp.ClientSession(headers=self._ws_headers) as ws_session:
            async with ws_session.ws_connect(self._ws_url) as ws:
                print(f"processing {req.url} on {self.provider_name}")
                request_str = req.as_raw_request_str()
                await ws.send_str(request_str)
                headers = await ws.__anext__()
                content = await ws.__anext__()

        res = Response.from_wsmessages(headers, content)
        return res

    @property
    def _ws_headers(self):
        app_key = self.cluster._engine._api_config.app_key  # pylint: disable=protected-access
        return {"Authorization": f"Bearer {app_key}"}

    @property
    def _ws_url(self):
        return self.network_node.get_websocket_uri(80)
