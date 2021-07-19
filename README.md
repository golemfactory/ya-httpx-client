# ya-httpx-client

Communicate with a provider-based http server the way you communicate with any other http server

## Introduction

The documentation assumes reader knows what [Golem](https://www.golem.network/) is and understand basics of the 
development of [yapapi-based services](https://handbook.golem.network/requestor-tutorials/service-development).

Features:

1. Deploy a http server on a Golem provider in an easy way. There are no requirements on the server implementation
  (doesn't even have to be in python) except it must be capable of running in the [Golem provider image](https://handbook.golem.network/requestor-tutorials/convert-a-docker-image-into-a-golem-image).
2. Send requests to the provider-based server using [httpx](https://www.python-httpx.org/)`.AsyncClient`, the same way
   you would send them to any other http server. `httpx` is similar to more popular `requests`, but with async support.
3. Restart the service on a new provider every time current agreement is terminated, in a seamless way that ensures no request is ever lost.
4. Maintain multiple providers running the same server (efficient load balancing included).
5. Change the number of providers running the server in a dynamic way.

NOTE: features 3-5 are useful only if your server is stateless (i.e. request/response history never matters).

This library is built on top of [yapapi](https://github.com/golemfactory/yapapi), there is nothing here that couldn't be done with the pure `yapapi`.

## Quickstart

```python
#   1.  Initialize the session with yapapi.Golem configuration. This should be done exactly once. 
executor_cfg = {'budget': 10, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)

#   2.  Define a service. You may define as many services as you want, provided they have different urls.
@session.startup(
    #   All http requests directed to host "any_name" will be processed by ...
    url='http://any_name',
    #   ...a service running on provider, in VM based on this image ...
    image_hash='25f09e17c34433f979331edf4f3b47b2ca330ba2f8acbfe2e3dbd9c3',
    #   ... and to be more exact, by one of indistinguishable services running on different providers.
    #   This is the initial number of services that can be changed at any time by session.set_cluster_size().
    #   Also check "load balancing" section.
    init_cluster_size=1
)
def calculator_startup(ctx, listen_on):
    #   Start the http server in the background (service will be operating only after this finished).
    ctx.run("sh", "-c", "start_my_http_server.sh")

#   3.  Use the service(s)
async def run():
    async with session.client() as client:
        req_url = 'http://any_name/do/something'
        res = await client.post(req_url, json={'foo': 'bar'})
        assert res.status_code == 200

    #   This is necessary for a graceful shutdown
    await session.close()

#   4.  Optional: change the number of services. Check "load balancing" section for more details.
session.set_cluster_size('http://any_name', 7)
```

## Load balancing

By default, a single instance of a service is created. We can change this by setting `init_cluster_size` in `@session.startup`
to a different value, or by calling `session.set_cluster_size`. This value doesn't have to be an integer, it might also be a
callable that takes a `ya_httpx_client.session.Cluster` object as an argument and returns an integer:

```python
def calculate_new_size(cluster):
    if cluster.request_queue.qsize() > 7:
        return 2
    else:
        return 1
session.set_cluster_size('http://any_name', calculate_new_size)
```

or even better, anything that could be evaluated as an integer:

```python
class LoadBalancer:
    def __init__(self, cluster):
        self.cluster = cluster
    
    def __int__(self):
        if self.cluster.request_queue.empty():
            return 0
        return 1
session.set_cluster_size('http://any_name', LoadBalancer)
```

If the last case, we have no control on how often `int(load_balancer_object)` will be called, so the implementation
should be a little more clever, at least to avoid too frequent changes - check [SimpleLoadBalancer](ya_httpx_client/provider_auto_balance.py)
for an example.

NOTE: setting size to anything other than an integer should be considered an experimental feature.
