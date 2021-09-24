import aiohttp
from yapapi.payload import vm

from .service_base import AbstractServiceBase
from ..serializable_request import Response


class VPNServiceBase(AbstractServiceBase):
    REQUIRED_CAPABILITIES = [vm.VM_CAPS_VPN]
    PROVIDER_URL = '0.0.0.0:80'

    async def run(self):
        self.instance_ws = self.network_node.get_websocket_uri(80)
        app_key = self.cluster._engine._api_config.app_key
        self.headers = {"Authorization": f"Bearer {app_key}"}

        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            print(f"processing {req.url} on {self.provider_name}")
            res = await self._handle_request(req)
            fut.set_result(res)

        #   We never get here, but `run` is supposed to be a generator, so we need a yield
        yield

    async def _handle_request(self, req):
        ws_session = aiohttp.ClientSession()
        async with ws_session.ws_connect(self.instance_ws, headers=self.headers) as ws:
            await ws.send_str(req.as_raw_request_str())
            headers = await ws.__anext__()
            content = await ws.__anext__()
        await ws_session.close()
        
        res = Response.from_headers_and_content(headers, content)
        return res
