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
    #   Test on upper because this doesn't matter
    assert req_1.method.upper() == req_2.method.upper()

    #   Test on path because the original host is not important
    assert urlparse(req_1.url).path == urlparse(req_2.url).path


@pytest.mark.parametrize('src_req', sample_requests)
def test_request(requestor_proxy, src_req: requests.Request):
# def test_request(src_req: requests.Request):
    prepped = src_req.prepare()
    session = requests.Session()

    res = session.send(prepped)

    assert res.status_code == 200

    echo_data = res.json()
    assert echo_data.get('echo') == 'echo'

    echo_req = requests.Request(**echo_data['req'])

    assert_requests_equal(src_req, echo_req)
