import asyncio
import sys
from typing import TYPE_CHECKING
if sys.version_info >= (3, 7):
    from contextlib import asynccontextmanager
else:
    from async_generator import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .serializable_request import Request
from .cluster import Cluster
from .network_wrapper import NetworkWrapper

if TYPE_CHECKING:
    from typing import Dict, Callable, SupportsInt, Union, AsyncGenerator, Tuple, Optional


class YagnaTransport(httpx.AsyncBaseTransport):
    '''
    https://www.python-httpx.org/advanced/#writing-custom-transports
    '''
    def __init__(self, request_queue):
        self.request_queue = request_queue

    async def handle_async_request(self, method, url, headers, stream, extensions):
        # pylint: disable=too-many-arguments
        req = Request.from_httpx_handle_request_args(method, url, headers, stream)
        fut = asyncio.Future()
        self.request_queue.put_nowait((req, fut))
        res = await fut
        return res.status, res.headers, httpx.ByteStream(res.data), {}


class Session:
    def __init__(self, executor_cfg: dict):
        self.manager = ServiceManager(executor_cfg)
        self.clusters: 'Dict[str, Cluster]' = {}
        self.network_wrapper = NetworkWrapper(self.manager)

    def set_cluster_size(self, url: str, size: 'Union[int, Callable[[Cluster], SupportsInt]]') -> None:
        self.clusters[url].set_size(size)

    def add_url(
        self,
        url: str,
        image_hash: str,
        entrypoint: 'Optional[Tuple[str, ...]]' = None,
        init_cluster_size: 'Union[int, Callable[[Cluster], SupportsInt]]' = 1
    ) -> None:
        if url in self.clusters:
            raise KeyError(f'Service for url {url} already exists')

        self.clusters[url] = Cluster(self.manager, image_hash, entrypoint, self.network_wrapper)
        self.set_cluster_size(url, init_cluster_size)

    @asynccontextmanager
    async def client(self, *args, **kwargs) -> 'AsyncGenerator[httpx.AsyncClient, None]':
        self.start_new_services()

        mounts = kwargs.pop('mounts', {})
        yagna_mounts = {url: YagnaTransport(cluster.request_queue) for url, cluster in self.clusters.items()}
        kwargs['mounts'] = {**mounts, **yagna_mounts}

        async with httpx.AsyncClient(*args, **kwargs) as client:
            yield client

    def start_new_services(self) -> None:
        for cluster in self.clusters.values():
            cluster.start()

    async def close(self) -> None:
        for cluster in self.clusters.values():
            cluster.stop()
        await self.network_wrapper.remove_network()
        await self.manager.close()
