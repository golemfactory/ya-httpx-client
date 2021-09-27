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


def assert_requests_equal(req_1: requests.Request, req_2: requests.Request):
    #   Test on lower because this doesn't matter
    assert req_1.method.lower() == req_2.method.lower()

    #   Test on path because the original host is not important
    assert urlparse(req_1.url).path == urlparse(req_2.url).path
    
    #   Headers - all lowercase
    lc_headers_1 = {k.lower(): v.lower() for k, v in req_1.headers.items()}
    lc_headers_2 = {k.lower(): v.lower() for k, v in req_2.headers.items()}
    assert sorted(lc_headers_1) == sorted(lc_headers_2)

    #   Data - testing on a prepared request because this is what we really care about
    #   (this will be sent) and requests have a very permissive interface.
    assert req_1.prepare().body == req_2.prepare().body


@pytest.mark.parametrize('src_req', sample_requests)
# def test_request(requestor_proxy, src_req: requests.Request):
def test_request(src_req: requests.Request):
    prepped = src_req.prepare()
    session = requests.Session()

    res = session.send(prepped)

    assert res.status_code == 200

    echo_data = res.json()
    assert echo_data.get('echo') == 'echo'

    echo_req = requests.Request(**echo_data['req'])

    assert_requests_equal(src_req, echo_req)
