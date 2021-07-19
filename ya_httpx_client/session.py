import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import httpx
from yapapi_service_manager import ServiceManager

from .service_base import ServiceBase
from .serializable_request import Request

if TYPE_CHECKING:
    from typing import Callable, Union, SupportsInt


class Cluster:
    '''
    Q: Here is a Cluster, and we have a `yapapi.Cluster`. Both seem to wrap a bunch of services.
       Do we need two separate clusters for this?
    A: In the future, this Cluster and `yapapi.Cluster` and also `yapapi_service_manager.ServiceWrapper`
       should be merged into the same cluster-wrapper-thingy, but we can't do this without yapapi-side modifications.
       Currently I don't think `yapapi.Cluster` could be used instead of this one.
    '''
    def __init__(self, manager: ServiceManager, image_hash: str, start_steps):
        self.manager = manager
        self.image_hash = image_hash
        self.start_steps = start_steps

        #   This is how many services we want to have running. It is set here to 0, but curretly
        #   every Cluster initialization is followed by a call to set_size, so this doesn't really matter.
        self.expected_cnt: 'Union[int, SupportsInt]' = 0

        #   Task that starts new services will be stored here (created later, because now we might not
        #   have a loop running yet)
        self.new_services_starter_task = None

        #   Each task in this lists corresponds to a single instance of yapapi_service_manager.ServiceWrapper
        #   (and thus to a single instance of a running service, assuming it already started)
        self.manager_tasks = []

        #   This queue is filled by YagnaTransport and emptied by Service instances
        self.request_queue = asyncio.Queue()

        #   This is a workaround for a missing yapapi feature
        self.cls = self._create_cls()

    @property
    def cnt(self):
        current_manager_tasks = [task for task in self.manager_tasks if not task.done()]
        return len(current_manager_tasks)

    def start(self):
        if self.new_services_starter_task is None:
            self.new_services_starter_task = asyncio.create_task(self._start_new_services())

    def stop(self):
        for task in self.manager_tasks:
            task.cancel()
        if self.new_services_starter_task is not None:
            self.new_services_starter_task.cancel()

    def set_size(self, size: 'Union[int, Callable[[Cluster], SupportsInt]]'):
        if isinstance(size, int):
            self.expected_cnt = size
        else:
            self.expected_cnt = size(self)

    async def _start_new_services(self):
        while True:
            expected_cnt = int(self.expected_cnt)
            new_tasks = [asyncio.create_task(self._manage_single_service()) for _ in range(self.cnt, expected_cnt)]
            self.manager_tasks += new_tasks
            await asyncio.sleep(1)

    async def _manage_single_service(self):
        service_wrapper = None

        while True:
            if service_wrapper is None:
                service_wrapper = self.manager.create_service(self.cls)

            if int(self.expected_cnt) < self.cnt:
                #   There are too many services running, (at least) one has to stop
                service_wrapper.stop()
                break

            await asyncio.sleep(1)

            if service_wrapper.status in ('pending', 'starting'):
                print(f"waiting for the service, current status: {service_wrapper.status}")
            elif service_wrapper.status == 'running':
                pass
            else:
                print(f"Replacing service on {service_wrapper.service.provider_name} - it is {service_wrapper.status}")
                service_wrapper.service.restart_failed_request()

                #   TODO: We don't stop the old service_wrapper, because it is dead either way.
                #         This way we distinguish "failed" and "stopped" wrappers (although we don't
                #         use this distinction). Think again if this is harmless.
                service_wrapper = None

    def _create_cls(self):
        #   NOTE: this is ugly, but we're waiting for https://github.com/golemfactory/yapapi/issues/372
        class_name = 'Service_' + uuid.uuid4().hex

        #   NOTE: 'yhc' is from `ya-httpx-client'
        return type(class_name, (ServiceBase,), {'_yhc_cluster': self})


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
