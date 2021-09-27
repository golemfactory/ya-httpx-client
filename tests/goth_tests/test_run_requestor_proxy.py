import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from goth.configuration import load_yaml
from goth.runner.log import configure_logging
from goth.runner import Runner
from goth.runner.probe import RequestorProbe

from .assertions import assert_no_errors

import requests

from ..sample_requests import sample_requests


logger = logging.getLogger("goth.test.run_proxy")


@pytest.fixture(scope='module')
def event_loop():
    """This overrides `pytest.asyncio` fixture"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
async def requestor_proxy(
    project_dir: Path, log_dir: Path, goth_config_path: Path
) -> None:
    goth_config = load_yaml(goth_config_path)
    requestor_script_path = project_dir / "examples" / "requestor_proxy" / "requestor_proxy.py"
    configure_logging(log_dir)
    runner = Runner(
        base_log_dir=log_dir,
        compose_config=goth_config.compose_config,
    )

    async with runner(goth_config.containers):

        requestor = runner.get_probes(probe_type=RequestorProbe)[0]

        async with requestor.run_command_on_host(
            f"{requestor_script_path} goth",
            env=os.environ,
        ) as (cmd_task, cmd_monitor):
            cmd_monitor.add_assertion(assert_no_errors)

            await cmd_monitor.wait_for_pattern(".*STARTED ON provider.*", timeout=200)
            logger.info("STARTED!")

            yield

            # cmd_task.cancel()


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


@pytest.mark.parametrize('src_req', sample_requests)
def test_request(requestor_proxy, src_req: requests.Request):
    prepped = src_req.prepare()
    session = requests.Session()

    res = session.send(prepped)

    assert res.status_code == 200

    echo_data = res.json()
    assert echo_data.get('echo') == 'echo'

    echo_req = requests.Request(**echo_data['req'])

    assert_requests_equal(src_req, prepped, echo_req)
