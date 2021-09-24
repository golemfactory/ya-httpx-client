import aiohttp
from yapapi.payload import vm

from .service_base import AbstractServiceBase
from ..serializable_request import Response


class VPNServiceBase(AbstractServiceBase):
    REQUIRED_CAPABILITIES = [vm.VM_CAPS_VPN]
    PROVIDER_URL = '0.0.0.0:80'

    async def run(self):
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            print(f"processing {req.url} on {self.provider_name}")
            res = await self._handle_request(req)
            fut.set_result(res)

        #   We never get here, but `run` is supposed to be a generator, so we need a yield
        yield

    async def _handle_request(self, req):
        query_string = req.path

        instance_ws = self.network_node.get_websocket_uri(80)
        app_key = self.cluster._engine._api_config.app_key

        ws_session = aiohttp.ClientSession()
        async with ws_session.ws_connect(
            instance_ws, headers={"Authorization": f"Bearer {app_key}"}
        ) as ws:
            print("GET ", query_string)
            await ws.send_str(f"GET {query_string} HTTP/1.0\r\n\r\n")
            headers = await ws.__anext__()
            print("HEADERS", headers)
            content = await ws.__anext__()
            data: bytes = content.data

            response_text = data.decode("utf-8")

        await ws_session.close()

        res = Response(200, response_text.encode(), {})
        return res
