# ya-httpx-client


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
    #   This is the initial number of services that can be changed at any time by session.set_size().
    #   Also check "load balancing" section.
    init_size=1
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
session.set_size('http://any_name', 7)
```

## Load balancing

By default, a single instance of a service is created. We can change this by setting `init_size` in `@session.startup`
to a different value, or by calling `session.set_size`. This value doesn't have to be an integer, it might also be a
callable that takes a `ya_httpx_client.session.Cluster` object as an argument and returns integer:

```python
def calculate_new_size(cluster):
    if cluster.request_queue.qsize() > 7:
        return 2
    else:
        return 1
session.set_size('http://any_name', calculate_new_size)
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
session.set_size('http://any_name', LoadBalancer)
```

If the last case, we have no control on how often `int(load_balancer_object)` will be called, so the implementation
should be a little more clever, at least to avoid too frequent changes - check [SimpleLoadBalancer](ya_httpx_client/provider_auto_balance)
for an example.
    
## Possible improvements

*   `startup` might be optional when https://github.com/golemfactory/yagna/issues/1350 is done
*   `on_service_stop` = [restart, raise, ignore]
*   faster communication when the VPN is ready
