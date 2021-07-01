import re
import asyncio
from contextlib import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .service_base import ServiceBase
from .serializable_request import Request


class YagnaTransport(httpx.AsyncBaseTransport):
    def __init__(self, request_queue):
        self.request_queue = request_queue

    async def handle_async_request(self, method, url, headers, stream, extensions):
        req = Request.from_httpx_handle_request_args(method, url, headers, stream)
        fut = asyncio.Future()
        self.request_queue.put_nowait((req, fut))
        await fut
        res = fut.result()
        return res.status, res.headers, httpx.ByteStream(res.data), {}


class Session:
    def __init__(self, executor_cfg):
        self.manager = ServiceManager(executor_cfg)
        self.service_defs = {}

    def startup(self, url, image_hash):
        if url in self.service_defs:
            raise KeyError(f'Service for url {url} already exists')

        def define_service(start_steps):
            request_queue = asyncio.Queue()
            self.service_defs[url] = {
                'image_hash': image_hash,
                'start_steps': start_steps,
                'queue': request_queue,
                'cnt': 1,
                'service_wrappers': []
            }

        return define_service

    @asynccontextmanager
    async def client(self, *args, **kwargs):
        await self.start_new_services()

        mounts = kwargs.pop('mounts', {})
        for url, service_def in self.service_defs.items():
            mounts[url] = YagnaTransport(service_def['queue'])
        kwargs['mounts'] = mounts

        async with httpx.AsyncClient(*args, **kwargs) as client:
            yield client

    async def start_new_services(self):
        start_services = []

        for url, service_def in self.service_defs.items():
            expected_cnt = service_def['cnt']
            current_cnt = len(service_def['service_wrappers'])
            start_services += [self._start_service(url) for _ in range(current_cnt, expected_cnt)]

        await asyncio.gather(*start_services)

    async def _start_service(self, url):
        #   NOTE: this additional class is because we're waiting for https://github.com/golemfactory/yapapi/issues/372
        class_name = 'Service' + re.sub(r'\W', '', url)
        cls = type(class_name, (ServiceBase,), {'_service_def': self.service_defs[url]})

        service_wrapper = self.manager.create_service(cls)
        self.service_defs[url]['service_wrappers'].append(service_wrapper)

        while True:
            if service_wrapper.status == 'running':
                return
            print(f"{url} status: {service_wrapper.status}")
            await asyncio.sleep(1)

    async def close(self):
        await self.manager.close()
