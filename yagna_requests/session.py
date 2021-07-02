import asyncio
import uuid
from contextlib import asynccontextmanager

import httpx
from yapapi_service_manager import ServiceManager

from .service_base import ServiceBase
from .serializable_request import Request


class Cluster:
    def __init__(self, manager, image_hash, start_steps, cnt):
        self.manager = manager
        self.image_hash = image_hash
        self.start_steps = start_steps
        self.cnt = cnt

        self.request_queue = asyncio.Queue()
        self.cls = self._create_cls()

        self.manager_tasks = []

    def start(self):
        current_cnt = len(self.manager_tasks)
        self.manager_tasks += [asyncio.create_task(self._manage()) for _ in range(current_cnt, self.cnt)]

    def stop(self):
        [task.cancel() for task in self.manager_tasks]

    async def _manage(self):
        service_wrapper = None

        while True:
            if service_wrapper is None:
                service_wrapper = self.manager.create_service(self.cls)

            await asyncio.sleep(1)

            if service_wrapper.status in ('pending', 'starting'):
                print(f"waiting for the service, current status: {service_wrapper.status}")
            elif service_wrapper.status == 'running':
                print(f"Service {service_wrapper.service.provider_name} is running")
            else:
                print(f"Restarting service because it is {service_wrapper.status}")
                service_wrapper.service.restart_failed_request()

                #   TODO: We don't stop the old service_wrapper, because it is dead either way.
                #         This is a todo because we don't know what to do with the "unresponsive" state of the
                #         service - we should either wait for it to start responding, or do service_wrapper.close().
                #         Currently I don't know if "unresponsive" ever happens at all.
                service_wrapper = None

    def _create_cls(self):
        #   NOTE: this is ugly, but we're waiting for https://github.com/golemfactory/yapapi/issues/372
        class_name = 'Service_' + uuid.uuid4().hex
        return type(class_name, (ServiceBase,), {'_yhc_cluster': self})


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
        self.clusters = {}

    def startup(self, url, image_hash, cnt=1):
        if url in self.clusters:
            raise KeyError(f'Service for url {url} already exists')

        def define_service(start_steps):
            self.clusters[url] = Cluster(self.manager, image_hash, start_steps, cnt)

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
        [cluster.start() for cluster in self.clusters.values()]

    async def close(self):
        [cluster.stop() for cluster in self.clusters.values()]
        await self.manager.close()
