import requests
from urllib.parse import urlparse


def assert_requests_equal(req_1: requests.Request, prep_1: requests.PreparedRequest, req_2: requests.Request):
    '''
    NOTE: prep_1 is assumed to be a prepared req_1.
          This is super-ugly but harmless, we do this to avoid as many request-specific testing/comparing
          issues as possible.
    '''
    #   Test on lower because this doesn't matter
    assert req_1.method.lower() == req_2.method.lower()

    #   Schema and host might change
    assert urlparse(req_1.url)[2:] == urlparse(req_2.url)[2:]

    #   Headers - all lowercase & from a prepared request because e.g. we need content-length
    prep_2 = req_2.prepare()
    lc_headers_1 = {k.lower(): v.lower() for k, v in prep_1.headers.items()}
    lc_headers_2 = {k.lower(): v.lower() for k, v in prep_2.headers.items()}

    for name in ('accept-encoding', 'host', 'user-agent'):
        #   Those headers are added somewhere by requests, so they are in returned request
        #   but not in the sent request -> this is a testing artifact -> don't compare them
        if name in lc_headers_1 and name not in lc_headers_2:
            del lc_headers_1[name]
        if name in lc_headers_2 and name not in lc_headers_1:
            del lc_headers_2[name]

    assert sorted(lc_headers_1) == sorted(lc_headers_2)

    #   Data
    body_1 = prep_1.body
    body_2 = prep_2.body

    if not body_1 and not body_2:
        return

    #   Encode both bodies (our echo server returns text whatever was sent --> testing artifact)
    if isinstance(body_1, str):
        body_1 = body_1.encode('utf-8')
    if isinstance(body_2, str):
        body_2 = body_2.encode('utf-8')

    #   Boundaries are random, here we replace one with the other
    boundary_1 = body_1[2:34]
    boundary_2 = body_2[2:34]
    body_2 = body_2.replace(boundary_2, boundary_1)

    assert body_1 == body_2
