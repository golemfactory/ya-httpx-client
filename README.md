# yagna-requests

I'd choose one from:
A)  rename to `yagna-httpx`
B)  remove httpx integration and
    B1) use requests "interface" but with `await`s
        `await session.get()`
    B2) use requests.Requests explicite
        `await session.send(Request('GET', ...))`
    B3) define some other interface?
    
    B2 is easier than B1, and B3 is not the best idea imho
(or maybe there are better options?)

`startup` might be optional when https://github.com/golemfactory/yagna/issues/1350 is done

Some libraries are required only on the provider side (requests, requests-unixsocket).
Others are required only on the requestor side (httpx, yapapi-service-manager).
They are entangled more than they should (e.g. `yagna_requests/serializable_request.py` requires requests
but only for the stuff running on provider).
--> untangle this
--> maybe there are some installation options like `yagna-requests[provider]`?

Load balance --> this should use multi-instance clusters --> consider changes in yapapi-service-manager
(that's not very important)
