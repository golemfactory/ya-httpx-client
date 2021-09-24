from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

import aiohttp

from yapapi.services import Service
from yapapi.payload import vm
import shlex

from .serializable_request import Response

if TYPE_CHECKING:
    from yapapi.script import Script

PROVIDER_URL = '0.0.0.0:80'

USE_VPN = False


def _simple_proxy_start_steps(ctx, url):
    ctx.run("/docker-entrypoint.sh")
    ctx.run("/bin/chmod", "a+x", "/")
    msg = "Hello from inside Golem!"
    ctx.run(
        "/bin/sh",
        "-c",
        f"echo {shlex.quote(msg)} > /usr/share/nginx/html/index.html",
    )
    ctx.run("/usr/sbin/nginx")


class ServiceBase(Service):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.queue = self._yhc_cluster.request_queue  # pylint: disable=no-member

        self.current_req, self.current_fut = None, None

    @classmethod
    async def get_payload(cls):
        image_hash = cls._yhc_cluster.image_hash  # pylint: disable=no-member
        return await vm.repo(image_hash=image_hash, capabilities=[vm.VM_CAPS_VPN])

    async def start(self):
        async for script in super().start():
            yield script
        start_steps = self._yhc_cluster.start_steps  # pylint: disable=no-member
        # start_steps = _simple_proxy_start_steps
        start_steps(self._ctx, PROVIDER_URL)
        yield self._ctx.commit()
        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            print(f"processing {req.url} on {self.provider_name} VPN: {USE_VPN}")
            if USE_VPN:
                res = await self._handle_request_via_vpn(req)
            else:
                res = await self._handle_request_via_vpn(req)
                # with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
                #     yield self._handle_request_via_files_script(req, in_file.name, out_file.name)
                #     res = Response.from_file(out_file.name)
            fut.set_result(res)
        yield

    def _handle_request_via_files_script(self, req, in_fname, out_fname) -> 'Script':
        req.to_file(in_fname)
        script = self._ctx.new_script()
        script.upload_file(in_fname, '/golem/work/req.json')
        script.run('/bin/sh', '-c', f'python -m ya_httpx_client --url {PROVIDER_URL} req.json res.json')
        script.download_file('/golem/work/res.json', out_fname)
        return script

    async def _handle_request_via_vpn(self, req):
        res_str = await self.handle_request('/')
        res = Response(200, res_str.encode(), {})
        return res

    def restart_failed_request(self) -> None:
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))

    async def handle_request(self, query_string: str):
        """
        handle the request coming from the local HTTP server
        by passing it to the instance through the VPN
        """
        instance_ws = self.network_node.get_websocket_uri(80)
        app_key = self.cluster._engine._api_config.app_key

        ws_session = aiohttp.ClientSession()
        async with ws_session.ws_connect(
            instance_ws, headers={"Authorization": f"Bearer {app_key}"}
        ) as ws:
            await ws.send_str("GET / HTTP/1.0\r\n\r\n")
            headers = await ws.__anext__()
            content = await ws.__anext__()
            data: bytes = content.data

            response_text = data.decode("utf-8")

        await ws_session.close()
        return response_text
