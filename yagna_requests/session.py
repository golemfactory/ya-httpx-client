import re
import asyncio
from contextlib import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .service_base import ServiceBase


class Session:
    def __init__(self, executor_cfg):
        self.manager = ServiceManager(executor_cfg)
        self.service_defs = {}
        self.service_wrappers = {}

    def startup(self, url, image_hash):
        if url in self.service_defs:
            raise KeyError(f'Service for url {url} already exists')

        def define_service(start_steps):
            self.service_defs[url] = {'image_hash': image_hash, 'start_steps': start_steps}

        return define_service

    async def send(self, url, req):
        service = self.service_wrappers[url].service
        return await service.send(req)

    @asynccontextmanager
    async def client(self, *args, **kwargs):
        await self.start_new_services()
        async with httpx.AsyncClient(*args, **kwargs) as client:
            yield client

    async def start_new_services(self):
        new_urls = [url for url in self.service_defs.keys() if url not in self.service_wrappers]
        start_services = [self._start_service(url) for url in new_urls]
        await asyncio.gather(*start_services)

    async def _start_service(self, url):
        #   NOTE: this additional class is because we're waiting for https://github.com/golemfactory/yapapi/issues/372
        class_name = 'Service' + re.sub(r'\W', '', url)
        cls = type(class_name, (ServiceBase,), {'_service_def': self.service_defs[url]})

        service_wrapper = self.manager.create_service(cls)
        self.service_wrappers[url] = service_wrapper

        while True:
            if service_wrapper.status == 'running':
                return
            print(f"{url} status: {service_wrapper.status}")
            await asyncio.sleep(1)

    async def close(self):
        await self.manager.close()
