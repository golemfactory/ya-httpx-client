# yagna-requests

`startup` might disappear when https://github.com/golemfactory/yagna/issues/1350 is done

Some libraries are required only on the provider side (requests, requests-unixsocket).
Others are required only on the requestor side (httpx, yapapi-service-manager).
They are entangled more than they should (e.g. `yagna_requests/serializable_request.py` requires requests
but only for the stuff running on provider).
--> untangle this
--> maybe there are some installation options like `yagna-requests[provider]`?
