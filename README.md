# yagna-requests

## PLANNED FEATURES

* load balancing (assuming stateless services)
* additional more complex example, with multiple servers
* (maybe) high availability - recreating services if provider stops responding

## CURRENT PROBLEMS

### Interface / name

Name `yagna-request` made a lot more sense when we planned to use `requests` library.
We use `httpx` because it has the `async` interface (and looks like next-gen `requests`).

The only reason to use `httpx` - or `requests` or any other library - is to re-use a popular
interface. Like in "and this works just like `httpx.AsyncClient` with all it's goodies (timeouts, cookies etc)".

Options:

* A) Rename to `yagna-httpx` or maybe `yagna-httpx-client`, as there is only `client` here.
* B) Change the interface to look more like requests
  * B1) recreate requests "interface" but with `await`s -  `await yagna_requests.get(...)`
  * B2) use requests.Request `await session.send(requests.Request('GET', ...))`
* C) define some other interface?

I think A) is best - httpx is fine.

### Installation

Currently the same code is installed on the provider and requestor side.
Some dependencies are required only on the provider side (requests, requests-unixsocket).
Others are required only on the requestor side (httpx, yapapi-service-manager).

How to deal with this? 
Maybe there are some installation options like `yagna-requests[provider]`?


## Random notes

* `startup` might be optional when https://github.com/golemfactory/yagna/issues/1350 is done
* Load balancing --> this should one day use multi-instance clusters (but not now, because it is not
  supported in yagna-service-manager and I'm not sure if `yapapi` is ready for e.g. recreating failed providers).
