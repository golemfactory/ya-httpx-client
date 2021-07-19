import asyncio
from contextlib import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .serializable_request import Request
from .cluster import Cluster


class YagnaTransport(httpx.AsyncBaseTransport):
    '''
    https://www.python-httpx.org/advanced/#writing-custom-transports
    '''
    def __init__(self, request_queue):
        self.request_queue = request_queue

    async def handle_async_request(self, method, url, headers, stream, extensions):
        req = Request.from_httpx_handle_request_args(method, url, headers, stream)
        fut = asyncio.Future()
        self.request_queue.put_nowait((req, fut))
        res = await fut
        return res.status, res.headers, httpx.ByteStream(res.data), {}


class Session:
    def __init__(self, executor_cfg):
        self.manager = ServiceManager(executor_cfg)
        self.clusters = {}

    def set_cluster_size(self, url, size):
        self.clusters[url].set_size(size)

    def startup(self, url, image_hash, init_size=1):
        if url in self.clusters:
            raise KeyError(f'Service for url {url} already exists')

        def define_service(start_steps):
            self.clusters[url] = Cluster(self.manager, image_hash, start_steps)
            self.set_cluster_size(url, init_size)

        return define_service

    @asynccontextmanager
    async def client(self, *args, **kwargs):
        self.start_new_services()

        mounts = kwargs.pop('mounts', {})
        yagna_mounts = {url: YagnaTransport(cluster.request_queue) for url, cluster in self.clusters.items()}
        kwargs['mounts'] = {**mounts, **yagna_mounts}

        async with httpx.AsyncClient(*args, **kwargs) as client:
            yield client

    def start_new_services(self):
        for cluster in self.clusters.values():
            cluster.start()

    async def close(self):
        for cluster in self.clusters.values():
            cluster.stop()
        await self.manager.close()
