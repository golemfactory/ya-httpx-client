import asyncio
from tempfile import NamedTemporaryFile

from yapapi.services import Service
from yapapi.payload import vm

from .serializable_request import Response

PROVIDER_SERVER_URL = 'unix:///tmp/golem.sock'


class ServiceBase(Service):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_queue = asyncio.Queue()

    @classmethod
    async def get_payload(cls):
        print("SERVICE DEF", cls._service_def)
        return await vm.repo(image_hash=cls._service_def['image_hash'])

    async def start(self):
        start_steps = self._service_def['start_steps']
        start_steps(self._ctx, PROVIDER_SERVER_URL)
        yield self._ctx.commit()
        print("STARTED")

    async def run(self):
        while True:
            fut = await self.commit_queue.get()
            res = yield self._ctx.commit()
            fut.set_result(res.result())

    async def commit(self):
        fut = asyncio.get_running_loop().create_future()
        self.commit_queue.put_nowait(fut)
        await fut
        return fut.result()

    async def send(self, req):
        with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
            req.to_file(in_file.name)
            self._ctx.send_file(in_file.name, '/golem/work/req.json')
            self._ctx.run('/bin/sh', '-c', f'python -m yagna_requests --url {PROVIDER_SERVER_URL} req.json res.json')
            self._ctx.download_file('/golem/work/res.json', out_file.name)

            await self.commit()

            res = Response.from_file(out_file.name)
            return res

        return res
