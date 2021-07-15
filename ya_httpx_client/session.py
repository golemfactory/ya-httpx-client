import asyncio
import uuid
from contextlib import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .service_base import ServiceBase
from .serializable_request import Request


class Cluster:
    '''
    Q: Here is a Cluster, and we have a `yapapi.Cluster`. Both seem to wrap a bunch of services.
       Do we need two separate clusters for this?
    A: In the future, this Cluster and `yapapi.Cluster` and also `yapapi_service_manager.ServiceWrapper`
       should be merged into the same cluster-wrapper-thingy, but we can't do this without yapapi-side modifications.
       Currently I don't think `yapapi.Cluster` could be used instead of this one.
    '''
    def __init__(self, manager, image_hash, start_steps, cnt):
        self.manager = manager
        self.image_hash = image_hash
        self.start_steps = start_steps

        self.expected_cnt = cnt

        self.request_queue = asyncio.Queue()
        self.cls = self._create_cls()

        self.new_services_starter_task = None
        self.manager_tasks = []

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

    def resize(self, new_cnt):
        self.expected_cnt = new_cnt

    async def _start_new_services(self):
        while True:
            new_tasks = [asyncio.create_task(self._manage()) for _ in range(self.cnt, self.expected_cnt)]
            if new_tasks:
                print(f"CREATED {len(new_tasks)} NEW TASKS")
            self.manager_tasks += new_tasks
            await asyncio.sleep(0.1)

    async def _manage(self):
        service_wrapper = None

        while True:
            if service_wrapper is None:
                service_wrapper = self.manager.create_service(self.cls)

            if self.expected_cnt < self.cnt:
                print("STOPPING BECAUSE THERE IS TOO MUCH OF US")
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

        #   NOTE: 'yhc' is from `yapapi-httpx-client', but I hope this will be removed before we release this
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

    def resize(self, url, cnt):
        self.clusters[url].resize(cnt)

    def startup(self, url, image_hash, service_cnt=1):
        if url in self.clusters:
            raise KeyError(f'Service for url {url} already exists')

        def define_service(start_steps):
            self.clusters[url] = Cluster(self.manager, image_hash, start_steps, service_cnt)

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
